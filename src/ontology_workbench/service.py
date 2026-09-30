from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

from ontology_workbench.atlas import PLATFORM_LABELS, build_assessment_package
from ontology_workbench.bim_importer import build_bim_import_bundle
from ontology_workbench.context_scanner import (
    build_business_context_inventory,
    build_document_chunks,
    extract_text_from_bytes,
    load_llm_settings,
)
from ontology_workbench.exporters import export_project_json, export_project_markdown
from ontology_workbench.external_metadata import parse_columns_csv, parse_sql_ddl
from ontology_workbench.models import (
    Concept,
    DataSource,
    DocumentRecord,
    OntologyProject,
    Relation,
    UseCase,
    ValidationIssue,
    utc_now_iso,
)
from ontology_workbench.nexo import build_model_element, build_ontology_release, build_registry_draft
from ontology_workbench.nexo_curation import build_consolidation_suggestions
from ontology_workbench.nexo_diff import compare_nexo_artifacts
from ontology_workbench.interoperability import TARGETS, build_publication_package
from ontology_workbench.fabric_adapter import (
    FABRIC_QUERY_BINDING_TABLES,
    discover_fabric_metadata as run_fabric_metadata_discovery,
    execute_fabric_read_only_query,
    fabric_connection_check,
)
from ontology_workbench.local_data_adapter import execute_local_synthetic_query
from ontology_workbench.mariadb_adapter import (
    check_mariadb_connection,
    execute_mariadb_read_only_query,
)
from ontology_workbench.semantic_model_importer import (
    normalize_semantic_model_api_payload,
    parse_pbip_zip,
    parse_tmdl_text,
)
from ontology_workbench.mariadb_schema import parse_mariadb_schema_dump
from ontology_workbench.connection_profiles import ConnectionProfileStore
from ontology_workbench.runtime import (
    investigate_context_pack,
    investigate_context_pack_with_llm,
)
from ontology_workbench.query_catalog import (
    catalog_for_context,
    extract_query_parameters,
    ordered_query_parameters,
    select_catalog_query,
)
from ontology_workbench.runtime_evaluation import evaluate_context_pack, suggest_evaluation_cases
from ontology_workbench.storage import ProjectStore


SOURCE_FORMAT_PLATFORMS = {
    "model.bim": "powerbi",
    "tmdl": "powerbi",
    "pbip": "powerbi",
    "semantic-model-api": "powerbi",
    "mariadb-schema": "mariadb",
    "fabric-information-schema": "fabric",
}
USE_CASE_PRIORITIES = ("alta", "media", "baja")


class WorkbenchService:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.connection_profiles = ConnectionProfileStore(store.root_dir.parent / "connections")

    def list_projects(self) -> list[OntologyProject]:
        projects = [self.store.load_project(project_id) for project_id in self.store.list_project_ids()]
        return sorted(projects, key=lambda project: project.updated_at, reverse=True)

    def create_project(
        self, name: str, description: str = "", project_id: str | None = None
    ) -> OntologyProject:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name is required")

        clean_project_id = (
            self._scope_id(project_id, "Project id")
            if project_id is not None
            else self._next_available_id(self._slugify(clean_name), self.store.project_exists)
        )
        if self.store.project_exists(clean_project_id):
            raise ValueError(f"Project already exists: {clean_project_id}")
        project = OntologyProject(
            id=clean_project_id,
            name=clean_name,
            description=description.strip(),
        )
        self.store.save_project(project)
        return project

    def get_project(self, project_id: str) -> OntologyProject:
        return self.store.load_project(project_id)

    def list_runtime_investigations(
        self, project_id: str, release_id: str
    ) -> list[dict[str, object]]:
        return self.store.list_runtime_investigations(project_id, release_id)

    def runtime_retention_report(
        self, project_id: str, release_id: str, keep_latest: int = 100
    ) -> dict[str, object]:
        return self.store.runtime_retention_report(project_id, release_id, keep_latest)

    def load_runtime_investigation(
        self, project_id: str, release_id: str, investigation_id: str
    ) -> dict[str, object]:
        return self.store.load_runtime_investigation(project_id, release_id, investigation_id)

    def update_project(self, project_id: str, name: str, description: str = "") -> OntologyProject:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name is required")

        project = self.store.load_project(project_id)
        project.name = clean_name
        project.description = description.strip()
        project.touch()
        self.store.save_project(project)
        return project

    def add_concept(
        self,
        project_id: str,
        name: str,
        definition: str = "",
        status: str = "draft",
        tags: list[str] | None = None,
    ) -> OntologyProject:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Concept name is required")

        project = self.store.load_project(project_id)
        concept_id = self._next_available_id(
            self._slugify(clean_name),
            lambda candidate: any(concept.id == candidate for concept in project.concepts),
        )
        concept = Concept(
            id=concept_id,
            name=clean_name,
            definition=definition.strip(),
            status=status.strip() or "draft",
            tags=[item.strip() for item in (tags or []) if item.strip()],
        )
        project.concepts.append(concept)
        project.touch()
        self.store.save_project(project)
        return project

    def add_relation(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        description: str = "",
    ) -> OntologyProject:
        clean_type = relation_type.strip()
        if not clean_type:
            raise ValueError("Relation type is required")

        project = self.store.load_project(project_id)
        concept_ids = {concept.id for concept in project.concepts}
        if source_id not in concept_ids or target_id not in concept_ids:
            raise ValueError("Relation endpoints must reference existing concepts")

        relation_seed = f"{source_id}-{clean_type}-{target_id}"
        relation_id = self._next_available_id(
            self._slugify(relation_seed),
            lambda candidate: any(relation.id == candidate for relation in project.relations),
        )
        relation = Relation(
            id=relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=clean_type,
            description=description.strip(),
        )
        project.relations.append(relation)
        project.touch()
        self.store.save_project(project)
        return project

    def update_concept(
        self,
        project_id: str,
        concept_id: str,
        name: str,
        definition: str = "",
        status: str = "draft",
        tags: list[str] | None = None,
    ) -> OntologyProject:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Concept name is required")

        project = self.store.load_project(project_id)
        concept = next((item for item in project.concepts if item.id == concept_id), None)
        if concept is None:
            raise ValueError("Concept not found")

        concept.name = clean_name
        concept.definition = definition.strip()
        concept.status = status.strip() or "draft"
        concept.tags = [item.strip() for item in (tags or []) if item.strip()]
        project.touch()
        self.store.save_project(project)
        return project

    def delete_concept(self, project_id: str, concept_id: str) -> OntologyProject:
        project = self.store.load_project(project_id)
        remaining_concepts = [concept for concept in project.concepts if concept.id != concept_id]
        if len(remaining_concepts) == len(project.concepts):
            raise ValueError("Concept not found")

        project.concepts = remaining_concepts
        project.relations = [
            relation
            for relation in project.relations
            if relation.source_id != concept_id and relation.target_id != concept_id
        ]
        project.touch()
        self.store.save_project(project)
        return project

    def update_relation(
        self,
        project_id: str,
        relation_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        description: str = "",
    ) -> OntologyProject:
        clean_type = relation_type.strip()
        if not clean_type:
            raise ValueError("Relation type is required")

        project = self.store.load_project(project_id)
        concept_ids = {concept.id for concept in project.concepts}
        if source_id not in concept_ids or target_id not in concept_ids:
            raise ValueError("Relation endpoints must reference existing concepts")

        relation = next((item for item in project.relations if item.id == relation_id), None)
        if relation is None:
            raise ValueError("Relation not found")

        relation.source_id = source_id
        relation.target_id = target_id
        relation.relation_type = clean_type
        relation.description = description.strip()
        project.touch()
        self.store.save_project(project)
        return project

    def delete_relation(self, project_id: str, relation_id: str) -> OntologyProject:
        project = self.store.load_project(project_id)
        remaining_relations = [relation for relation in project.relations if relation.id != relation_id]
        if len(remaining_relations) == len(project.relations):
            raise ValueError("Relation not found")

        project.relations = remaining_relations
        project.touch()
        self.store.save_project(project)
        return project

    def update_metadata(self, project_id: str, metadata: dict[str, str]) -> OntologyProject:
        project = self.store.load_project(project_id)
        project.metadata = {key.strip(): value.strip() for key, value in metadata.items() if key.strip()}
        project.touch()
        self.store.save_project(project)
        return project

    def update_assessment_scope(
        self, project_id: str, client_id: str, domain_id: str, data_product_id: str, owner: str = ""
    ) -> OntologyProject:
        project = self.store.load_project(project_id)
        project.metadata.update(
            {
                "client_id": self._scope_id(client_id, "Client"),
                "domain_id": self._scope_id(domain_id, "Domain"),
                "data_product_id": self._scope_id(data_product_id, "Data product"),
            }
        )
        if owner.strip():
            project.metadata["owner"] = owner.strip()
        else:
            project.metadata.pop("owner", None)
        project.touch()
        self.store.save_project(project)
        return project

    def list_data_sources(self, project_id: str) -> list[DataSource]:
        return list(self.store.load_project(project_id).sources)

    def register_data_source(
        self,
        project_id: str,
        name: str,
        platform: str,
        owner: str = "",
        description: str = "",
        access_mode: str = "external_file",
    ) -> DataSource:
        """Declare a system in assessment scope before (or without) loading its metadata."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("El nombre del sistema es obligatorio")
        if platform not in PLATFORM_LABELS:
            raise ValueError(f"Plataforma no soportada: {platform}")
        project = self.store.load_project(project_id)
        source = DataSource(
            source_id=self._next_available_id(
                self._slugify(clean_name),
                lambda candidate: any(item.source_id == candidate for item in project.sources),
            ),
            name=clean_name,
            platform=platform,
            owner=owner.strip(),
            description=description.strip(),
            access_mode=access_mode,
        )
        project.sources.append(source)
        project.touch()
        self.store.save_project(project)
        return source

    def update_data_source(
        self, project_id: str, source_id: str, name: str, platform: str, owner: str = "", description: str = ""
    ) -> DataSource:
        if not name.strip():
            raise ValueError("El nombre del sistema es obligatorio")
        if platform not in PLATFORM_LABELS:
            raise ValueError(f"Plataforma no soportada: {platform}")
        project = self.store.load_project(project_id)
        source = self._find_source(project, source_id)
        source.name = name.strip()
        source.platform = platform
        source.owner = owner.strip()
        source.description = description.strip()
        for concept in project.concepts:
            if concept.metadata.get("source.id") == source_id:
                concept.metadata["source.platform"] = platform
        project.touch()
        self.store.save_project(project)
        return source

    def delete_data_source(self, project_id: str, source_id: str) -> dict[str, int]:
        """Remove a system from scope together with the objects inventoried from it."""
        project = self.store.load_project(project_id)
        self._find_source(project, source_id)
        self.store.create_snapshot(project, note=f"before-delete-source-{source_id}")
        removed = self._remove_source_objects(project, source_id)
        project.sources = [item for item in project.sources if item.source_id != source_id]
        for use_case in project.use_cases:
            use_case.source_ids = [item for item in use_case.source_ids if item != source_id]
        project.touch()
        self.store.save_project(project)
        return {"removed_objects": removed}

    def import_source_metadata_file(
        self, project_id: str, source_id: str, filename: str, content: bytes
    ) -> tuple[OntologyProject, dict[str, int]]:
        """Inventory one system from an exported file; re-importing replaces that system's objects."""
        suffix = Path(filename).suffix.casefold()
        if suffix in {".bim", ".json", ".tmdl", ".pbip", ".zip"}:
            return self.import_semantic_model_file(project_id, filename, content, source_id=source_id)
        text = content.decode("utf-8-sig", errors="replace")
        if suffix in {".sql", ".ddl"}:
            parsed = parse_sql_ddl(text)
        elif suffix in {".csv", ".tsv", ".txt"}:
            parsed = parse_columns_csv(text)
        else:
            raise ValueError("Formato no soportado; use .sql/.ddl, .csv, .bim, .tmdl o PBIP .zip")
        source_metadata = self.store.save_technical_source(
            project_id, filename, content, source_format=str(parsed["source_format"])
        )
        return self.import_bim_model(
            project_id,
            dict(parsed["model"]),
            snapshot_note=f"before-source-import-{source_id}",
            source_metadata=source_metadata,
            source_id=source_id,
        )

    def add_use_case(
        self,
        project_id: str,
        name: str,
        business_question: str = "",
        owner: str = "",
        priority: str = "media",
        source_ids: list[str] | None = None,
    ) -> UseCase:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("El nombre del caso de uso es obligatorio")
        if priority not in USE_CASE_PRIORITIES:
            raise ValueError("Prioridad invalida")
        project = self.store.load_project(project_id)
        use_case = UseCase(
            use_case_id=self._next_available_id(
                self._slugify(clean_name),
                lambda candidate: any(item.use_case_id == candidate for item in project.use_cases),
            ),
            name=clean_name,
            business_question=business_question.strip(),
            owner=owner.strip(),
            priority=priority,
            source_ids=list(source_ids or []),
        )
        project.use_cases.append(use_case)
        project.touch()
        self.store.save_project(project)
        return use_case

    def delete_use_case(self, project_id: str, use_case_id: str) -> None:
        project = self.store.load_project(project_id)
        remaining = [item for item in project.use_cases if item.use_case_id != use_case_id]
        if len(remaining) == len(project.use_cases):
            raise ValueError("Caso de uso no encontrado")
        project.use_cases = remaining
        project.touch()
        self.store.save_project(project)

    def _find_source(self, project: OntologyProject, source_id: str) -> DataSource:
        source = next((item for item in project.sources if item.source_id == source_id), None)
        if source is None:
            raise ValueError(f"Sistema no encontrado: {source_id}")
        return source

    def _resolve_source(
        self, project: OntologyProject, source_id: str | None, source_metadata: dict[str, str]
    ) -> DataSource:
        if source_id:
            return self._find_source(project, source_id)
        source_format = source_metadata.get("source.format", "")
        platform = SOURCE_FORMAT_PLATFORMS.get(source_format, "other")
        stem = Path(source_metadata.get("source.technical.filename", "") or source_format or "modelo").stem
        derived_id = self._slugify(f"{platform}-{stem}")
        existing = next((item for item in project.sources if item.source_id == derived_id), None)
        if existing:
            return existing
        source = DataSource(source_id=derived_id, name=stem, platform=platform)
        project.sources.append(source)
        return source

    def _remove_source_objects(self, project: OntologyProject, source_id: str) -> int:
        removed_ids = {
            concept.id for concept in project.concepts if concept.metadata.get("source.id") == source_id
        }
        project.concepts = [concept for concept in project.concepts if concept.id not in removed_ids]
        project.relations = [
            relation
            for relation in project.relations
            if relation.source_id not in removed_ids and relation.target_id not in removed_ids
        ]
        return len(removed_ids)

    def _mark_source_inventoried(
        self,
        source: DataSource,
        source_metadata: dict[str, str],
        counts: dict[str, int],
    ) -> None:
        source.status = "inventoried"
        source.source_format = source_metadata.get("source.format", source.source_format)
        source.filename = source_metadata.get("source.technical.filename", source.filename)
        source.stored_path = source_metadata.get("source.technical.path", source.stored_path)
        source.content_sha256 = source_metadata.get("source.technical.sha256", source.content_sha256)
        source.inventoried_at = utc_now_iso()
        source.object_counts = {key: int(value) for key, value in counts.items()}

    def save_mariadb_connection_profile(
        self,
        project_id: str,
        profile_id: str,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> dict[str, str]:
        self.store.load_project(project_id)
        summary = self.connection_profiles.save_mariadb_profile(
            project_id, profile_id, host, port, user, password, database
        )
        return {
            "project_id": summary.project_id,
            "profile_id": summary.profile_id,
            "adapter": summary.adapter,
            "path": str(summary.path),
        }

    def list_connection_profiles(self, project_id: str) -> list[dict[str, str]]:
        self.store.load_project(project_id)
        return [
            {
                "project_id": item.project_id,
                "profile_id": item.profile_id,
                "adapter": item.adapter,
                "path": str(item.path),
            }
            for item in self.connection_profiles.list(project_id)
        ]

    def check_mariadb_connection(self, project_id: str, profile_id: str) -> dict[str, str]:
        self.store.load_project(project_id)
        profile_path = self.connection_profiles.profile_path(project_id, profile_id)
        return check_mariadb_connection(profile_path)

    def create_snapshot(self, project_id: str, note: str = ""):
        project = self.store.load_project(project_id)
        return self.store.create_snapshot(project, note=note)

    def list_snapshots(self, project_id: str):
        return self.store.list_snapshots(project_id)

    def restore_snapshot(self, project_id: str, snapshot_id: str) -> OntologyProject:
        project = self.store.load_snapshot_project(project_id, snapshot_id)
        project.touch()
        self.store.save_project(project)
        return project

    def validate_project(self, project_id: str) -> list[ValidationIssue]:
        project = self.store.load_project(project_id)
        issues: list[ValidationIssue] = []

        seen_names: set[tuple[str, str]] = set()
        for concept in project.concepts:
            normalized_name = (concept.metadata.get("source.id", ""), concept.name.strip().lower())
            if normalized_name in seen_names:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        code="duplicate-concept-name",
                        message=f"El concepto '{concept.name}' aparece mas de una vez.",
                    )
                )
            else:
                seen_names.add(normalized_name)

            if not concept.definition.strip():
                issues.append(
                    ValidationIssue(
                        level="info",
                        code="missing-definition",
                        message=f"El concepto '{concept.name}' no tiene definicion.",
                    )
                )

        concept_ids = {concept.id for concept in project.concepts}
        relation_signatures: set[tuple[str, str, str]] = set()
        related_nodes: set[str] = set()
        for relation in project.relations:
            if relation.source_id not in concept_ids or relation.target_id not in concept_ids:
                issues.append(
                    ValidationIssue(
                        level="error",
                        code="dangling-relation",
                        message=f"La relacion '{relation.id}' referencia conceptos inexistentes.",
                    )
                )
                continue

            signature = (relation.source_id, relation.relation_type.strip().lower(), relation.target_id)
            if signature in relation_signatures:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        code="duplicate-relation",
                        message=f"La relacion '{relation.id}' duplica otra relacion existente.",
                    )
                )
            else:
                relation_signatures.add(signature)

            if relation.source_id == relation.target_id:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        code="self-relation",
                        message=f"La relacion '{relation.id}' apunta al mismo concepto como origen y destino.",
                    )
                )

            related_nodes.add(relation.source_id)
            related_nodes.add(relation.target_id)

        isolated_concepts = [concept.name for concept in project.concepts if concept.id not in related_nodes]
        for concept_name in isolated_concepts:
            issues.append(
                ValidationIssue(
                    level="info",
                    code="isolated-concept",
                    message=f"El concepto '{concept_name}' no participa en ninguna relacion.",
                )
            )

        return issues

    def export_project_json(self, project_id: str) -> str:
        project = self.store.load_project(project_id)
        return export_project_json(project, self.validate_project(project_id))

    def export_project_markdown(self, project_id: str) -> str:
        project = self.store.load_project(project_id)
        return export_project_markdown(project, self.validate_project(project_id))

    def import_project(self, payload: dict[str, object], preserve_project_id: bool = False) -> OntologyProject:
        project_blob = payload.get("project", payload)
        if not isinstance(project_blob, dict):
            raise ValueError("Invalid project payload")

        imported = OntologyProject.from_dict(project_blob)
        imported.id = (
            imported.id if preserve_project_id and not self.store.project_exists(imported.id)
            else self._next_available_id(self._slugify(imported.name), self.store.project_exists)
        )
        imported.touch()
        self.store.save_project(imported)
        return imported

    def import_bim_model(
        self,
        project_id: str,
        payload: dict[str, object],
        clear_existing: bool = False,
        snapshot_note: str = "",
        source_metadata: dict[str, str] | None = None,
        source_id: str | None = None,
    ) -> tuple[OntologyProject, dict[str, int]]:
        project = self.store.load_project(project_id)
        if project.concepts or project.relations or project.metadata:
            self.store.create_snapshot(project, note=snapshot_note.strip() or "before-bim-import")

        if clear_existing:
            project.concepts = []
            project.relations = []
            for existing_source in project.sources:
                existing_source.status = "declared"
                existing_source.object_counts = {}
        source = None
        if source_id or source_metadata:
            source = self._resolve_source(project, source_id, source_metadata or {})
            self._remove_source_objects(project, source.source_id)
        bundle = build_bim_import_bundle(
            payload,
            existing_concept_ids={concept.id for concept in project.concepts},
            existing_relation_ids={relation.id for relation in project.relations},
            slugify=self._slugify,
            source_label=str((source_metadata or {}).get("source.format", "model.bim")),
        )
        if source is not None:
            for concept in bundle.concepts:
                concept.metadata["source.id"] = source.source_id
                concept.metadata["source.platform"] = source.platform
            self._mark_source_inventoried(source, source_metadata or {}, bundle.summary)

        project.concepts.extend(bundle.concepts)
        project.relations.extend(bundle.relations)
        project.metadata.update(bundle.metadata)
        if source_metadata:
            project.metadata.update(source_metadata)
        project.touch()
        self.store.save_project(project)
        return project, bundle.summary

    def import_bim_file(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        clear_existing: bool = False,
        snapshot_note: str = "",
    ) -> tuple[OntologyProject, dict[str, int]]:
        """Import and retain a local model.bim source as assessment evidence."""
        try:
            payload = json.loads(content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("model.bim no contiene JSON UTF-8 valido") from exc
        if not isinstance(payload, dict):
            raise ValueError("model.bim invalido: se esperaba un objeto JSON")
        source_metadata = self.store.save_technical_source(
            project_id, filename, content, source_format="model.bim"
        )
        return self.import_bim_model(
            project_id,
            payload,
            clear_existing=clear_existing,
            snapshot_note=snapshot_note,
            source_metadata=source_metadata,
        )

    def import_semantic_model_file(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        clear_existing: bool = False,
        snapshot_note: str = "",
        source_id: str | None = None,
    ) -> tuple[OntologyProject, dict[str, int]]:
        """Import TMDL or PBIP semantic-model metadata through the BIM contract."""
        suffix = Path(filename).suffix.casefold()
        if suffix in {".bim", ".json"}:
            try:
                payload = json.loads(content.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("model.bim no contiene JSON UTF-8 valido") from exc
            if not isinstance(payload, dict):
                raise ValueError("model.bim invalido: se esperaba un objeto JSON")
            source_format = "model.bim"
        elif suffix == ".tmdl":
            try:
                payload = parse_tmdl_text(content.decode("utf-8-sig"))
            except UnicodeDecodeError as exc:
                raise ValueError("El archivo TMDL no es UTF-8 valido") from exc
            source_format = "tmdl"
        elif suffix in {".pbip", ".zip"}:
            payload = parse_pbip_zip(content)
            source_format = "pbip"
        else:
            raise ValueError("Formato no soportado; use .tmdl o un paquete PBIP .zip")
        source_metadata = self.store.save_technical_source(
            project_id, filename, content, source_format=source_format
        )
        return self.import_bim_model(
            project_id,
            payload,
            clear_existing=clear_existing,
            snapshot_note=snapshot_note,
            source_metadata=source_metadata,
            source_id=source_id,
        )

    def import_semantic_model_api_payload(
        self,
        project_id: str,
        payload: dict[str, object],
        endpoint_label: str = "semantic-model-api",
        clear_existing: bool = False,
        snapshot_note: str = "",
    ) -> tuple[OntologyProject, dict[str, int]]:
        """Import a previously retrieved semantic-model API response.

        Authentication and network access stay outside this local adapter.
        """
        normalized = normalize_semantic_model_api_payload(payload)
        serialized = json.dumps(normalized, indent=2, ensure_ascii=False).encode("utf-8")
        source_metadata = self.store.save_technical_source(
            project_id,
            "semantic-model-api.json",
            serialized,
            source_format="semantic-model-api",
        )
        source_metadata["source.api.endpoint"] = endpoint_label.strip() or "semantic-model-api"
        return self.import_bim_model(
            project_id,
            normalized,
            clear_existing=clear_existing,
            snapshot_note=snapshot_note,
            source_metadata=source_metadata,
        )

    def import_mariadb_schema_file(
        self,
        project_id: str,
        path: Path,
        clear_existing: bool = False,
        snapshot_note: str = "",
        source_id: str | None = None,
    ) -> tuple[OntologyProject, dict[str, int]]:
        """Import only MariaDB DDL; INSERT rows are never converted into ontology objects."""
        source_path = Path(path).expanduser()
        schema = parse_mariadb_schema_dump(source_path)
        source_metadata = {
            "source.format": "mariadb-schema",
            "source.technical.filename": source_path.name,
            "source.technical.path": str(source_path.resolve()),
            "source.technical.sha256": self._file_sha256(source_path),
            "mariadb.tables": str(schema["table_count"]),
            "mariadb.columns": str(schema["column_count"]),
            "mariadb.relationships": str(schema["relationship_count"]),
        }
        return self.import_bim_model(
            project_id,
            dict(schema["model"]),
            clear_existing=clear_existing,
            snapshot_note=snapshot_note,
            source_metadata=source_metadata,
            source_id=source_id,
        )

    def upload_context_document(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        doc_type: str,
        content_type: str = "application/octet-stream",
    ) -> DocumentRecord:
        if not filename.strip():
            raise ValueError("Document filename is required")

        document_id, stored_path = self.store.save_document(project_id, filename, content)
        extracted_text = extract_text_from_bytes(filename, content)
        extracted_text_path = self.store.save_extracted_text(project_id, document_id, extracted_text)
        documents = self.store.list_documents(project_id)
        document = DocumentRecord(
            document_id=document_id,
            project_id=project_id,
            filename=Path(filename).name,
            stored_path=str(stored_path),
            doc_type=doc_type.strip() or "misc",
            content_type=content_type,
            uploaded_at=utc_now_iso(),
            extraction_status="extracted" if extracted_text.strip() else "empty",
            extracted_text_path=str(extracted_text_path),
            extracted_chars=len(extracted_text),
        )
        documents.append(document)
        self.store.save_documents_manifest(project_id, documents)
        return document

    def list_context_documents(self, project_id: str) -> list[DocumentRecord]:
        return self.store.list_documents(project_id)

    def get_context_document_integrity(self, project_id: str) -> dict[str, object]:
        documents = self.store.list_documents(project_id)
        by_id: dict[str, list[str]] = {}
        for document in documents:
            by_id.setdefault(document.document_id, []).append(document.filename)
        duplicates = {
            document_id: filenames
            for document_id, filenames in by_id.items()
            if len(filenames) > 1
        }
        return {
            "documents": len(documents),
            "duplicate_document_ids": duplicates,
            "is_valid": not duplicates,
        }

    def repair_context_document_ids(self, project_id: str) -> dict[str, int]:
        """Re-extract duplicate legacy documents with new IDs and invalidate stale context."""
        documents = self.store.list_documents(project_id)
        integrity = self.get_context_document_integrity(project_id)
        duplicate_ids = set(dict(integrity["duplicate_document_ids"]))
        if not duplicate_ids:
            return {"repaired": 0, "missing_sources": 0}

        repaired = 0
        missing_sources = 0
        for document in documents:
            if document.document_id not in duplicate_ids:
                continue
            document.document_id = self.store.new_document_id()
            source_path = Path(document.stored_path)
            if source_path.exists() and source_path.is_file():
                extracted_text = extract_text_from_bytes(document.filename, source_path.read_bytes())
                document.extracted_text_path = str(
                    self.store.save_extracted_text(project_id, document.document_id, extracted_text)
                )
                document.extracted_chars = len(extracted_text)
                document.extraction_status = "extracted" if extracted_text.strip() else "empty"
                document.notes = (document.notes + " | " if document.notes else "") + "re-extracted-after-id-repair"
            else:
                missing_sources += 1
                document.extracted_text_path = ""
                document.extracted_chars = 0
                document.extraction_status = "missing_source"
                document.notes = (document.notes + " | " if document.notes else "") + "source-missing-during-id-repair"
            repaired += 1

        self.store.save_documents_manifest(project_id, documents)
        self.store.invalidate_business_context_inventory(
            project_id,
            "Document identifiers were repaired; regenerate the scanner inventory from re-extracted sources.",
        )
        return {"repaired": repaired, "missing_sources": missing_sources}

    def scan_business_context(self, project_id: str) -> dict[str, object]:
        project = self.store.load_project(project_id)
        documents = self.store.list_documents(project_id)
        if not documents:
            raise ValueError("No hay documentos cargados para analizar")

        texts = {
            document.document_id: self.store.load_document_text(project_id, document.document_id)
            for document in documents
        }
        chunks = build_document_chunks(documents, texts)
        self.store.save_context_chunks(project_id, chunks)
        inventory = build_business_context_inventory(project, documents, texts, chunks=chunks)
        self.store.save_business_context_inventory(project_id, inventory)
        return inventory

    def get_business_context_inventory(self, project_id: str) -> dict[str, object] | None:
        return self.store.load_business_context_inventory(project_id)

    def create_atlas_assessment(
        self,
        project_id: str,
        client_id: str,
        domain_id: str,
        data_product_id: str,
    ) -> dict[str, object]:
        """Generate the first reproducible Atlas assessment package for a local project."""
        project = self.store.load_project(project_id)
        clean_client_id = self._scope_id(client_id, "Client")
        clean_domain_id = self._scope_id(domain_id, "Domain")
        clean_data_product_id = self._scope_id(data_product_id, "Data product")
        run_id = f"atlas-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        documents = self.store.list_documents(project_id)
        source_hashes = {
            f"{document.document_id}:{document.filename}": self._file_sha256(Path(document.stored_path))
            for document in documents
        }
        context_chunks = self.store.load_context_chunks(project_id)
        if not context_chunks:
            document_texts = {
                document.document_id: self.store.load_document_text(project_id, document.document_id)
                for document in documents
            }
            context_chunks = build_document_chunks(documents, document_texts)
            self.store.save_context_chunks(project_id, context_chunks)
        package = build_assessment_package(
            project=project,
            documents=documents,
            business_context=self.store.load_business_context_inventory(project_id),
            context_chunks=context_chunks,
            source_hashes=source_hashes,
            client_id=clean_client_id,
            domain_id=clean_domain_id,
            data_product_id=clean_data_product_id,
            run_id=run_id,
        )
        package_path = self.store.save_atlas_assessment(package)
        package["package_path"] = str(package_path)
        return package

    def execute_fabric_validation_query(
        self, query_name: str, parameters: tuple[object, ...] = ()
    ) -> dict[str, object]:
        if parameters:
            return execute_fabric_read_only_query(query_name, parameters)
        return execute_fabric_read_only_query(query_name)

    def list_atlas_assessments(self, project_id: str) -> list[dict[str, object]]:
        return self.store.list_atlas_assessments(project_id)

    def get_atlas_assessment(self, project_id: str, run_id: str) -> dict[str, object]:
        return self.store.load_atlas_package(project_id, run_id)

    def update_atlas_review(
        self,
        project_id: str,
        run_id: str,
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, object]:
        """Record the human decision about an Atlas baseline without approving an ontology."""
        if status != "pending_review" and not reviewer.strip():
            raise ValueError("Reviewer is required when closing or escalating an Atlas review")
        return self.store.update_atlas_review(
            project_id, run_id, status, reviewer, reviewer_role, note
        )

    def create_nexo_draft(
        self,
        project_id: str,
        assessment_run_id: str,
        source_authority: str = "technical",
        query_catalog: object = None,
    ) -> dict[str, object]:
        project = self.store.load_project(project_id)
        assessment = next(
            (
                item
                for item in self.store.list_atlas_assessments(project_id)
                if item.get("run_id") == assessment_run_id
            ),
            None,
        )
        if assessment is None:
            raise FileNotFoundError(f"Atlas assessment not found: {assessment_run_id}")
        package_path = Path(str(assessment["package_path"]))
        inventory_path = package_path / "business_context_inventory.json"
        semantic_inventory_path = package_path / "semantic_inventory.json"
        if not inventory_path.exists():
            raise ValueError("El assessment Atlas no contiene inventario de contexto de negocio")
        if not semantic_inventory_path.exists():
            raise ValueError("El assessment Atlas no contiene inventario técnico")
        business_context = json.loads(inventory_path.read_text(encoding="utf-8"))
        semantic_inventory = json.loads(semantic_inventory_path.read_text(encoding="utf-8"))
        if business_context.get("status") == "invalidated":
            raise ValueError("El contexto de negocio del assessment fue invalidado y debe regenerarse")
        draft_id = f"nexo-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        draft = build_registry_draft(
            project,
            assessment,
            business_context,
            semantic_inventory,
            draft_id,
            source_authority=source_authority,
            query_catalog=query_catalog,
        )
        draft_path = self.store.save_nexo_draft(draft)
        draft["draft_path"] = str(draft_path)
        return draft

    def list_nexo_drafts(self, project_id: str) -> list[dict[str, object]]:
        return self.store.list_nexo_drafts(project_id)

    def get_nexo_draft(self, project_id: str, draft_id: str) -> dict[str, object]:
        return self.store.load_nexo_draft(project_id, draft_id)

    def update_nexo_candidate(
        self,
        project_id: str,
        draft_id: str,
        candidate_id: str,
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, object]:
        if status in {"approved", "rejected"} and not reviewer.strip():
            raise ValueError("Reviewer is required to approve or reject a Nexo candidate")
        return self.store.update_nexo_candidate(
            project_id, draft_id, candidate_id, status, reviewer, reviewer_role, note
        )

    def bulk_update_nexo_candidates(
        self,
        project_id: str,
        draft_id: str,
        candidate_ids: list[str],
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, int]:
        if not reviewer.strip():
            raise ValueError("Reviewer is required for a bulk Nexo decision")
        return self.store.bulk_update_nexo_candidates(
            project_id, draft_id, candidate_ids, status, reviewer, reviewer_role, note
        )

    def add_nexo_model_element(
        self,
        project_id: str,
        draft_id: str,
        element_type: str,
        name: str,
        definition: str,
        owner: str,
        linked_candidate_ids: list[str],
    ) -> dict[str, object]:
        element_id = f"model-{element_type.strip().lower()}-{uuid.uuid4().hex[:12]}"
        element = build_model_element(
            element_id, element_type, name, definition, owner, linked_candidate_ids
        )
        return self.store.add_nexo_model_element(project_id, draft_id, element)

    def propose_nexo_source_bindings(
        self, project_id: str, draft_id: str
    ) -> dict[str, int]:
        """Create pending source-binding proposals for unique deterministic matches."""
        draft = self.store.load_nexo_draft(project_id, draft_id)
        existing = {
            tuple(str(item) for item in element.get("linked_candidate_ids", []))
            for element in draft.get("model_elements", [])
            if element.get("element_type") == "source_binding"
        }
        created = 0
        skipped_ambiguous = 0
        for candidate in draft["candidates"]:
            match = candidate.get("technical_match")
            if not isinstance(match, dict) or match.get("status") != "matched":
                if isinstance(match, dict) and match.get("status") == "ambiguous":
                    skipped_ambiguous += 1
                continue
            asset_ids = [str(item) for item in match.get("technical_asset_ids", [])]
            if len(asset_ids) != 1:
                continue
            links = (str(candidate["candidate_id"]), asset_ids[0])
            if links in existing:
                continue
            element = build_model_element(
                f"model-source-binding-{uuid.uuid4().hex[:12]}",
                "source_binding",
                f"{candidate['name']} -> {asset_ids[0]}",
                "Binding técnico propuesto por coincidencia determinista; requiere revisión humana.",
                "",
                list(links),
            )
            self.store.add_nexo_model_element(project_id, draft_id, element)
            existing.add(links)
            created += 1
        return {"created": created, "skipped_ambiguous": skipped_ambiguous}

    def update_nexo_model_element(
        self,
        project_id: str,
        draft_id: str,
        element_id: str,
        status: str,
        reviewer: str,
        reviewer_role: str,
        note: str,
    ) -> dict[str, object]:
        if status in {"approved", "rejected"} and not reviewer.strip():
            raise ValueError("Reviewer is required to approve or reject a Nexo model element")
        return self.store.update_nexo_model_element(
            project_id, draft_id, element_id, status, reviewer, reviewer_role, note
        )

    def publish_nexo_release(
        self, project_id: str, draft_id: str, released_by: str, release_note: str
    ) -> dict[str, object]:
        if not released_by.strip():
            raise ValueError("Released by is required")
        draft = self.store.load_nexo_draft(project_id, draft_id)
        release_id = f"release-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        release = build_ontology_release(draft, release_id, released_by.strip(), release_note.strip())
        package_path = self.store.save_nexo_release(project_id, release)
        release["package_path"] = str(package_path)
        return release

    def generate_nexo_consolidation_suggestions(
        self, project_id: str, draft_id: str
    ) -> dict[str, object]:
        draft = self.store.load_nexo_draft(project_id, draft_id)
        package = build_consolidation_suggestions(list(draft["candidates"]))
        self.store.save_nexo_consolidation_suggestions(project_id, draft_id, package)
        return package

    def get_nexo_consolidation_suggestions(
        self, project_id: str, draft_id: str
    ) -> dict[str, object] | None:
        return self.store.load_nexo_consolidation_suggestions(project_id, draft_id)

    def update_nexo_consolidation_suggestion(
        self,
        project_id: str,
        draft_id: str,
        suggestion_id: str,
        status: str,
        reviewer: str,
        note: str,
    ) -> dict[str, object]:
        if status != "pending_review" and not reviewer.strip():
            raise ValueError("Reviewer is required to decide a consolidation suggestion")
        return self.store.update_nexo_consolidation_suggestion(
            project_id, draft_id, suggestion_id, status, reviewer, note
        )

    def apply_nexo_consolidation_suggestion(
        self, project_id: str, draft_id: str, suggestion_id: str, reviewer: str, note: str
    ) -> dict[str, object]:
        if not reviewer.strip():
            raise ValueError("Reviewer is required to apply a consolidation")
        return self.store.apply_nexo_consolidation_suggestion(
            project_id, draft_id, suggestion_id, reviewer, note
        )

    def list_nexo_releases(self, project_id: str) -> list[dict[str, object]]:
        return self.store.list_nexo_releases(project_id)

    def compare_nexo_draft_to_release(
        self, project_id: str, draft_id: str, baseline_release_id: str
    ) -> dict[str, object]:
        comparison = compare_nexo_artifacts(
            {"kind": "release", "payload": self.store.load_nexo_release(project_id, baseline_release_id)},
            {"kind": "draft", "payload": self.store.load_nexo_draft(project_id, draft_id)},
        )
        comparison["comparison_path"] = str(self.store.save_nexo_comparison(project_id, comparison))
        return comparison

    def compare_nexo_releases(
        self, project_id: str, baseline_release_id: str, candidate_release_id: str
    ) -> dict[str, object]:
        if baseline_release_id == candidate_release_id:
            raise ValueError("Seleccione dos releases diferentes para comparar")
        comparison = compare_nexo_artifacts(
            {"kind": "release", "payload": self.store.load_nexo_release(project_id, baseline_release_id)},
            {"kind": "release", "payload": self.store.load_nexo_release(project_id, candidate_release_id)},
        )
        comparison["comparison_path"] = str(self.store.save_nexo_comparison(project_id, comparison))
        return comparison

    def prepare_interoperability_package(
        self,
        project_id: str,
        release_id: str,
        target: str,
        prepared_by: str,
        note: str,
        settings: dict[str, str] | None = None,
    ) -> dict[str, object]:
        release = self.store.load_nexo_release(project_id, release_id)
        package_id = f"mapping-{target.strip().lower()}-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        package = build_publication_package(release, target, prepared_by, note, package_id, settings)
        package["package_path"] = str(self.store.save_interoperability_package(project_id, package))
        return package

    def interoperability_targets(self) -> dict[str, dict[str, str]]:
        return TARGETS

    def check_fabric_connection(self) -> dict[str, str]:
        return fabric_connection_check()

    def discover_fabric_metadata(
        self, project_id: str, table_name_pattern: str = ""
        , schema_name: str = ""
    ) -> dict[str, object]:
        discovery_id = f"fabric-discovery-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        discovery = run_fabric_metadata_discovery(
            table_name_pattern=table_name_pattern, schema_name=schema_name
        )
        discovery["discovery_id"] = discovery_id
        discovery["project_id"] = project_id
        discovery["package_path"] = str(
            self.store.save_fabric_discovery(project_id, discovery_id, discovery)
        )
        return discovery

    def import_fabric_metadata(
        self, project_id: str, discovery: dict[str, object]
    ) -> dict[str, int]:
        if str(discovery.get("project_id", "")) != project_id:
            raise ValueError("El inventario Fabric pertenece a otro proyecto")
        tables = [item for item in discovery.get("tables", []) if isinstance(item, dict)]
        columns = [item for item in discovery.get("columns", []) if isinstance(item, dict)]
        if not tables and not columns:
            raise ValueError("El inventario Fabric no contiene metadata para importar")
        project = self.store.load_project(project_id)
        fabric_source_id = self._slugify(f"fabric-{discovery.get('database') or 'warehouse'}")
        fabric_source = next(
            (item for item in project.sources if item.source_id == fabric_source_id), None
        )
        if fabric_source is None:
            fabric_source = DataSource(
                source_id=fabric_source_id,
                name=f"Fabric {discovery.get('database') or 'warehouse'}",
                platform="fabric",
                access_mode="live_read_only",
            )
            project.sources.append(fabric_source)
        source_tags = {"source.id": fabric_source_id, "source.platform": "fabric"}
        existing_ids = {concept.id for concept in project.concepts}
        existing_relation_ids = {relation.id for relation in project.relations}
        table_ids: dict[tuple[str, str], str] = {}
        added = 0
        for table in tables:
            schema = str(table.get("schema", "dbo"))
            name = str(table.get("name", "")).strip()
            if not name:
                continue
            concept_id = self._slugify(f"fabric-{schema}-{name}")
            table_ids[(schema, name)] = concept_id
            if concept_id in existing_ids:
                continue
            project.concepts.append(
                Concept(
                    id=concept_id,
                    name=f"{schema}.{name}",
                    status="imported",
                    tags=["table", "fabric"],
                    metadata={
                        "fabric.objectType": "table",
                        "fabric.schema": schema,
                        "fabric.table": name,
                        **source_tags,
                    },
                )
            )
            existing_ids.add(concept_id)
            added += 1
        for column in columns:
            schema = str(column.get("schema", "dbo"))
            table_name = str(column.get("table", "")).strip()
            name = str(column.get("name", "")).strip()
            if not table_name or not name:
                continue
            concept_id = self._slugify(f"fabric-{schema}-{table_name}-{name}")
            if concept_id not in existing_ids:
                project.concepts.append(
                    Concept(
                        id=concept_id,
                        name=f"{schema}.{table_name}.{name}",
                        status="imported",
                        tags=["column", "fabric"],
                        metadata={
                            "fabric.objectType": "column",
                            "fabric.schema": schema,
                            "fabric.table": table_name,
                            "fabric.column": name,
                            "fabric.dataType": str(column.get("data_type", "")),
                            "fabric.nullable": str(column.get("nullable", "")),
                            **source_tags,
                        },
                    )
                )
                existing_ids.add(concept_id)
                added += 1
            table_id = table_ids.get((schema, table_name))
            if table_id:
                relation_id = self._slugify(
                    f"fabric-{schema}-{table_name}-contains-column-{name}"
                )
                if relation_id not in existing_relation_ids:
                    project.relations.append(
                        Relation(
                            id=relation_id,
                            source_id=table_id,
                            target_id=concept_id,
                            relation_type="contains-column",
                            description="Contencion derivada de INFORMATION_SCHEMA de Fabric",
                        )
                    )
                    existing_relation_ids.add(relation_id)
        for concept in project.concepts:
            if concept.metadata.get("fabric.objectType") and not concept.metadata.get("source.id"):
                concept.metadata.update(source_tags)
        package_path = Path(str(discovery.get("package_path", "")))
        source_path = package_path / "metadata_inventory.json"
        fabric_metadata = {
            "source.format": "fabric-information-schema",
            "source.technical.path": str(source_path),
            "source.technical.filename": "metadata_inventory.json",
            "source.technical.sha256": self._file_sha256(source_path),
        }
        self._mark_source_inventoried(
            fabric_source,
            fabric_metadata,
            {
                "tables": sum(c.metadata.get("source.id") == fabric_source_id and "table" in c.tags for c in project.concepts),
                "columns": sum(c.metadata.get("source.id") == fabric_source_id and "column" in c.tags for c in project.concepts),
            },
        )
        project.metadata.update(
            {
                **fabric_metadata,
                "fabric.server": str(discovery.get("server", "")),
                "fabric.database": str(discovery.get("database", "")),
            }
        )
        project.touch()
        self.store.save_project(project)
        return {"added": added, "tables": len(tables), "columns": len(columns)}

    def investigate_release(self, project_id: str, release_id: str, question: str) -> dict[str, object]:
        if not question.strip():
            raise ValueError("Question is required")
        release = self.store.load_nexo_release(project_id, release_id)
        context_pack = json.loads((Path(str(release["package_path"])) / "agent_context_pack.json").read_text(encoding="utf-8"))
        investigation_id = f"argos-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        if _requests_direct_sql(question):
            investigation = investigate_context_pack(context_pack, question.strip(), investigation_id)
            investigation["answer"] = (
                "Me abstengo: Argos no ejecuta SQL recibido desde la pregunta. "
                "Use una capacidad aprobada del catalogo."
            )
            investigation["interpretation"] = (
                "La pregunta fue bloqueada antes del routing y no se ejecuto ninguna consulta."
            )
            investigation["manifest"]["status"] = "abstained"
            investigation["reasoning_advisory"] = _reasoning_advisory(question, None)
            investigation["llm_used"] = False
            investigation["package_path"] = str(self.store.save_runtime_investigation(project_id, investigation))
            return investigation
        settings = load_llm_settings()
        if settings.enabled:
            investigation = investigate_context_pack_with_llm(
                context_pack,
                question.strip(),
                investigation_id,
                settings,
                _argos_query_catalog(context_pack),
                lambda query_name, parameters: self._execute_llm_selected_query(
                    project_id, context_pack, query_name, parameters
                ),
            )
            investigation["reasoning_advisory"] = _llm_reasoning_advisory(settings)
            investigation["llm_used"] = True
            investigation["package_path"] = str(self.store.save_runtime_investigation(project_id, investigation))
            return investigation

        investigation = investigate_context_pack(context_pack, question.strip(), investigation_id)
        query_catalog = _argos_query_catalog(context_pack)
        query_name = select_catalog_query(question, query_catalog)
        investigation["reasoning_advisory"] = _reasoning_advisory(question, query_name)
        if query_name is None and _requests_catalog_capability(question):
            investigation["answer"] = (
                "Me abstengo: la release activa de este proyecto no tiene una consulta aprobada "
                "para esa capacidad. Revise el catalogo de Argos o agregue una operacion allowlisted."
            )
            investigation["interpretation"] = (
                "No se uso ninguna consulta de otro proyecto ni se genero SQL fuera del catalogo aprobado."
            )
            investigation["manifest"]["status"] = "abstained"
        if query_name and _has_query_binding(context_pack, query_name):
            specification = query_catalog[query_name]
            extracted = extract_query_parameters(question, specification)
            parameters = ordered_query_parameters(specification, extracted)
            query_result = self._execute_catalog_query(project_id, context_pack, query_name, parameters)
            investigation["live_query"] = query_result
            adapter = str(specification.get("adapter", "fabric"))
            investigation["manifest"]["mode"] = f"deterministic-context-pack-plus-{adapter}-read-only"
            if query_name == "risk_rule_sic" and not query_result.get("rows"):
                investigation["answer"] = (
                    "Me abstengo: Fabric no contiene un resultado para la regla y SIC solicitados."
                )
                investigation["manifest"]["status"] = "abstained"
            else:
                investigation["answer"] = _format_fabric_query_answer(query_name, query_result)
                investigation["interpretation"] = _format_fabric_query_interpretation(
                    query_name, query_result
                )
                if _requests_visualization(question):
                    investigation["visualization"] = _build_fabric_visualization(query_name, query_result)
                investigation["manifest"]["status"] = "answered"
                investigation["suggested_questions"] = _suggest_follow_up_questions(
                    query_name, query_result
                )
        investigation["package_path"] = str(self.store.save_runtime_investigation(project_id, investigation))
        return investigation

    def _execute_llm_selected_query(
        self,
        project_id: str,
        context_pack: dict[str, object],
        query_name: str,
        parameters: object,
    ) -> dict[str, object]:
        if not _has_query_binding(context_pack, query_name):
            return {"status": "not_executed", "query_name": query_name, "rows": []}
        specification = _argos_query_catalog(context_pack).get(query_name)
        if specification is None:
            return {"status": "not_executed", "query_name": query_name, "rows": []}
        try:
            ordered = ordered_query_parameters(specification, parameters)
        except ValueError:
            return {"status": "invalid_parameters", "query_name": query_name, "rows": []}
        return self._execute_catalog_query(project_id, context_pack, query_name, ordered)

    def _execute_catalog_query(
        self,
        project_id: str | dict[str, object],
        context_pack: dict[str, object] | str,
        query_name: str | tuple[object, ...],
        parameters: tuple[object, ...] = (),
    ) -> dict[str, object]:
        if isinstance(project_id, dict):
            legacy_context_pack = project_id
            legacy_query_name = str(context_pack)
            legacy_parameters = query_name if isinstance(query_name, tuple) else parameters
            project_id = str(legacy_context_pack.get("project_id", ""))
            context_pack = legacy_context_pack
            query_name = legacy_query_name
            parameters = legacy_parameters
        if not isinstance(context_pack, dict) or not isinstance(query_name, str):
            return {"status": "not_executed", "query_name": str(query_name), "rows": []}
        specification = _argos_query_catalog(context_pack).get(query_name)
        if specification is None:
            return {"status": "not_executed", "query_name": query_name, "rows": []}
        template_id = str(specification.get("template_id", query_name))
        adapter = str(specification.get("adapter", "fabric")).casefold()
        if adapter == "fabric":
            return self.execute_fabric_validation_query(template_id, parameters)
        if adapter == "local_synthetic":
            return execute_local_synthetic_query(
                template_id,
                parameters,
                int(specification.get("max_rows", 100)),
            )
        if adapter == "mariadb":
            connection_profile = str(specification.get("connection_profile", "")).strip()
            if not connection_profile:
                return {
                    "status": "missing_connection_profile",
                    "query_name": query_name,
                    "rows": [],
                }
            profile_path = self.connection_profiles.profile_path(
                project_id, connection_profile
            )
            return execute_mariadb_read_only_query(
                template_id,
                parameters,
                int(specification.get("max_rows", 100)),
                config_path=profile_path,
            )
        return {"status": "not_executed", "query_name": query_name, "rows": []}

    def suggest_argos_evaluation_cases(
        self, project_id: str, release_id: str
    ) -> list[dict[str, str]]:
        context_pack = self._load_release_context_pack(project_id, release_id)
        return suggest_evaluation_cases(context_pack)

    def evaluate_argos_release(
        self, project_id: str, release_id: str, cases: list[dict[str, object]]
    ) -> dict[str, object]:
        if not cases:
            raise ValueError("Agregue al menos un caso de evaluación")
        context_pack = self._load_release_context_pack(project_id, release_id)
        evaluation_id = f"argos-evaluation-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        evaluation = evaluate_context_pack(
            context_pack,
            cases,
            evaluation_id,
            investigator=lambda question, investigation_id: self.investigate_release(
                project_id, release_id, question
            ),
        )
        evaluation["package_path"] = str(self.store.save_runtime_evaluation(project_id, evaluation))
        return evaluation

    def _load_release_context_pack(self, project_id: str, release_id: str) -> dict[str, object]:
        release = self.store.load_nexo_release(project_id, release_id)
        return json.loads((Path(str(release["package_path"])) / "agent_context_pack.json").read_text(encoding="utf-8"))

    def get_argos_query_catalog(
        self, project_id: str, release_id: str
    ) -> dict[str, dict[str, object]]:
        """Return only the approved query capabilities from this project's release."""
        return _argos_query_catalog(self._load_release_context_pack(project_id, release_id))

    def _next_available_id(self, seed: str, exists: callable) -> str:
        candidate = seed or "item"
        suffix = 2
        while exists(candidate):
            candidate = f"{seed}-{suffix}"
            suffix += 1
        return candidate

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "item"

    def _scope_id(self, value: str, label: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError(f"{label} is required")
        return self._slugify(clean_value)

    def _file_sha256(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()


def _format_fabric_query_answer(query_name: str, query_result: dict[str, object]) -> str:
    rows = [row for row in query_result.get("rows", []) if isinstance(row, dict)]
    if query_name == "order_status_summary":
        if not rows:
            return "Consulta MariaDB: no se encontraron pedidos."
        details = "; ".join(
            f"{row.get('estado', 'sin estado')}: {row.get('cantidad', 0)}"
            for row in rows
        )
        return f"Consulta MariaDB: pedidos por estado: {details}."
    if query_name == "sales_summary":
        if not rows:
            return "Consulta MariaDB: no se encontraron ventas en el periodo disponible."
        total_sales = sum((row.get("ventas", 0) or 0 for row in rows), 0)
        details = "; ".join(
            f"{row.get('periodo', 'sin periodo')}: {row.get('ventas', 0)}"
            for row in reversed(rows)
        )
        return (
            f"Consulta MariaDB: las ventas acumuladas son {total_sales} en "
            f"{len(rows)} mes(es). Evolucion mensual: {details}."
        )
    if query_name == "product_demand_by_year":
        if not rows:
            return "Consulta MariaDB: no se encontraron productos con pedidos en el año solicitado."
        year = query_result.get("parameters", ["el periodo"])[0]
        details = "; ".join(
            f"{index}. {row.get('nombre', row.get('producto_id', 'sin producto'))} "
            f"(codigo {row.get('codigo', 'sin codigo')}): "
            f"{row.get('unidades_solicitadas', 0)} unidades en {row.get('cantidad_pedidos', 0)} pedidos"
            for index, row in enumerate(rows, start=1)
        )
        return f"Consulta MariaDB: top de demanda de {year}: {details}."
    if query_name == "customer_debt":
        if not rows:
            return "Consulta MariaDB: no se encontro el cliente solicitado."
        row = rows[0]
        return (
            f"Consulta MariaDB: el cliente {row.get('nombre', row.get('id', 'sin ID'))} "
            f"tiene deuda registrada de {row.get('deuda', 0)} y saldo pendiente en pedidos "
            f"de {row.get('saldo_pedidos', 0)}."
        )
    if query_name == "product_availability":
        if not rows:
            return "Consulta MariaDB: no se encontraron productos."
        return (
            f"Consulta MariaDB: se obtuvieron {len(rows)} productos con stock actual, "
            "reservado y disponible."
        )
    if query_name == "sales_by_customer":
        if not rows:
            return "Consulta local sintetica: no hay ventas para ese cliente."
        row = rows[0]
        return (
            f"Consulta local sintetica: {row.get('customer_name', 'Cliente')} "
            f"({row.get('customer_id', 'sin ID')}) tiene {row.get('order_count', 0)} ventas, "
            f"por un neto de {row.get('net_sales', 0)} y un margen bruto de "
            f"{row.get('gross_margin', 0)}."
        )
    if query_name == "risk_summary" and rows:
        row = rows[0]
        return (
            f"Consulta real Fabric: {row.get('total_rows', 0)} registros de riesgo, "
            f"{row.get('distinct_sic', 0)} SIC distintos; última ejecución: "
            f"{row.get('latest_calculation', 'sin fecha')}."
        )
    if query_name == "impact_summary" and rows:
        row = rows[0]
        return (
            f"Consulta real Fabric: {row.get('reales', 0)} valores REAL, "
            f"{row.get('proxies', 0)} proxies, {row.get('pendientes', 0)} pendientes y "
            f"{row.get('no_disponibles', 0)} no disponibles."
        )
    if query_name == "risk_rule_sic":
        if not rows:
            return "Consulta real Fabric: no hay resultado para esa regla y SIC."
        row = rows[0]
        return (
            f"Consulta real Fabric: para la regla {row.get('id_risc')} en el SIC {row.get('sic')}, "
            f"el riesgo final es {row.get('riesgo_final_texto', 'sin nivel')} "
            f"({row.get('riesgo_final_num', 'sin valor')}). Se obtiene combinando "
            f"una probabilidad {row.get('probabilidad_final_texto', 'sin nivel')} "
            f"con un impacto {row.get('impacto_final_texto', 'sin nivel')}; "
            f"la matriz/metodo {row.get('metodo_calculo', 'sin informar')} produce ese nivel. "
            f"El calculo corresponde a {row.get('fecha_calculo', 'sin fecha')}."
        )
    if query_name == "risk_sic":
        if not rows:
            return "Consulta real Fabric: no hay riesgos registrados para ese SIC."
        details = "; ".join(
            f"regla {row.get('id_risc', 'sin regla')}: {row.get('riesgo_final_texto', 'sin nivel')}"
            for row in rows
        )
        return f"Consulta real Fabric: se encontraron {len(rows)} riesgos para el SIC {rows[0].get('sic', 'sin SIC')}. {details}."
    if query_name in {"risk_levels", "impact_statuses"}:
        if query_name == "impact_statuses":
            details = "; ".join(
                f"{row.get('tipo_valor', 'sin tipo')}/{row.get('estado', 'sin estado')}: {row.get('total_rows', 0)}"
                for row in rows
            )
            return f"Consulta real Fabric: {details}."
        details = "; ".join(
            f"{row.get('riesgo_final_texto', 'sin nivel')}: {row.get('total_rows', 0)}"
            for row in rows
        )
        return f"Consulta real Fabric: {details}."
    return "Consulta real Fabric ejecutada sin resultados agregados."


def _has_query_binding(context_pack: dict[str, object], query_name: str) -> bool:
    specification = catalog_for_context(context_pack).get(query_name, {})
    adapter = str(specification.get("adapter", "fabric")).casefold()
    default_binding = FABRIC_QUERY_BINDING_TABLES.get(query_name, "") if adapter == "fabric" else ""
    required_table = str(specification.get("binding_required", default_binding))
    if not required_table:
        return False
    has_explicit_binding = any(
        required_table in str(binding.get("name", ""))
        for binding in context_pack.get("data_bindings", [])
        if isinstance(binding, dict)
    )
    if has_explicit_binding:
        return True
    # Imported Fabric assets are approved technical bindings in the pilot release.
    return any(
        required_table in str(asset.get("name", ""))
        for asset in context_pack.get("technical_assets", [])
        if isinstance(asset, dict)
    )


def _has_fabric_query_binding(context_pack: dict[str, object], query_name: str) -> bool:
    return _has_query_binding(context_pack, query_name)


def _suggest_follow_up_questions(
    query_name: str, query_result: dict[str, object]
) -> list[str]:
    rows = [row for row in query_result.get("rows", []) if isinstance(row, dict)]
    if query_name != "risk_rule_sic" or not rows:
        return []
    row = rows[0]
    rule_id = row.get("id_risc", "")
    sic = row.get("sic", "")
    return [
        f"¿Qué probabilidad obtuvo la regla {rule_id} en el SIC {sic} y con qué evidencia?",
        f"¿Qué impacto obtuvo la regla {rule_id} en el SIC {sic} y con qué evidencia?",
        f"¿Cómo transforma la matriz 4x4 esos valores en el riesgo final de la regla {rule_id}?",
        f"¿Cuándo se calculó el riesgo de la regla {rule_id} en el SIC {sic} y qué método se utilizó?",
        f"¿Qué debería cambiar para reducir el riesgo de la regla {rule_id} en el SIC {sic}?",
    ]


def _reasoning_advisory(question: str, query_name: str | None) -> dict[str, str]:
    reasoning_terms = {
        "porque",
        "porqué",
        "por qué",
        "explica",
        "explicame",
        "justifica",
        "mejorar",
        "mejoraría",
        "causa",
        "causal",
    }
    normalized = question.casefold()
    requires_reasoning = any(term in normalized for term in reasoning_terms)
    settings = load_llm_settings()
    provider = settings.provider or "disabled"
    model = settings.model or "sin modelo configurado"
    if requires_reasoning:
        return {
            "level": "higher_reasoning_recommended",
            "model_used": "deterministic-runtime",
            "configured_provider": provider,
            "configured_model": model,
            "message": (
                "La respuesta factual se obtuvo con reglas y una consulta read-only. "
                "La pregunta pide causalidad o recomendacion; para responderla con rigor "
                "se necesita un LLM con mayor capacidad de razonamiento y evidencia adicional."
            ),
        }
    return {
        "level": "standard_reasoning_sufficient",
        "model_used": "deterministic-runtime",
        "configured_provider": provider,
        "configured_model": model,
        "message": (
            f"La pregunta se resolvio con la operacion {query_name or 'context-pack'}; "
            "no fue necesario usar un LLM."
        ),
    }


def _llm_reasoning_advisory(settings) -> dict[str, str]:
    return {
        "level": "llm_reasoning_active",
        "model_used": "configured-llm",
        "configured_provider": settings.provider,
        "configured_model": settings.model,
        "message": (
            "Argos utilizó el LLM configurado para interpretar la pregunta, decidir cómo investigarla "
            "y redactar la respuesta sobre el contexto aprobado."
        ),
    }


def _argos_query_catalog(context_pack: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        name: details
        for name, details in catalog_for_context(context_pack).items()
        if _has_query_binding(context_pack, name)
    }


def _requests_visualization(question: str) -> bool:
    normalized = question.casefold()
    return any(term in normalized for term in ("mermaid", "diagrama", "grafico", "gráfico"))


def _requests_direct_sql(question: str) -> bool:
    normalized = question.casefold()
    if re.search(r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke)\b", normalized):
        return True
    return bool(re.search(r"\bselect\b.+\b(from|where|join|group|order|limit)\b", normalized, re.DOTALL))


def _format_fabric_query_interpretation(
    query_name: str, query_result: dict[str, object]
) -> str:
    rows = [row for row in query_result.get("rows", []) if isinstance(row, dict)]
    if query_name == "sales_summary" and rows:
        return (
            "La serie suma importeTotal de pedidos no cancelados, agrupado por mes. "
            "Es una medida de ventas registradas en pedidos y no una inferencia sobre margen o cobros."
        )
    if query_name == "risk_rule_sic" and rows:
        row = rows[0]
        return (
            f"El nivel final {row.get('riesgo_final_texto', 'sin nivel')} se explica por la combinación "
            f"de probabilidad {row.get('probabilidad_final_texto', 'sin nivel')} e impacto "
            f"{row.get('impacto_final_texto', 'sin nivel')}, según el método "
            f"{row.get('metodo_calculo', 'sin informar')}. "
            "Esto es una interpretación de los campos devueltos, no una inferencia causal adicional."
        )
    return "La interpretación resume los valores devueltos por la consulta read-only; no agrega causalidad fuera de la evidencia."


def _requests_catalog_capability(question: str) -> bool:
    tokens = set(re.findall(r"[a-záéíóúñ0-9]+", question.casefold()))
    return bool(tokens.intersection({"venta", "ventas", "facturacion", "facturación", "evolucion", "evolución", "monto"}))


def _build_fabric_visualization(
    query_name: str, query_result: dict[str, object]
) -> dict[str, str]:
    rows = [row for row in query_result.get("rows", []) if isinstance(row, dict)]
    if query_name == "risk_rule_sic" and rows:
        row = rows[0]
        return {
            "type": "mermaid",
            "status": "generated_from_fabric_row",
            "code": (
                "graph LR\n"
                f"    P[Probabilidad: {row.get('probabilidad_final_texto', 'sin dato')}] --> M[Método: {row.get('metodo_calculo', 'sin dato')}]\n"
                f"    I[Impacto: {row.get('impacto_final_texto', 'sin dato')}] --> M\n"
                f"    M --> R[Riesgo final: {row.get('riesgo_final_texto', 'sin dato')}]"
            ),
        }
    return {
        "type": "mermaid",
        "status": "insufficient_evidence",
        "code": "graph TD\n    A[La consulta no devolvio una estructura causal graficable]",
    }
