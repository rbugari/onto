from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

from ontology_workbench.atlas import build_assessment_package
from ontology_workbench.bim_importer import build_bim_import_bundle
from ontology_workbench.context_scanner import (
    build_business_context_inventory,
    build_document_chunks,
    extract_text_from_bytes,
)
from ontology_workbench.exporters import export_project_json, export_project_markdown
from ontology_workbench.models import (
    Concept,
    DocumentRecord,
    OntologyProject,
    Relation,
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
from ontology_workbench.runtime import investigate_context_pack, select_fabric_query
from ontology_workbench.runtime_evaluation import evaluate_context_pack, suggest_evaluation_cases
from ontology_workbench.storage import ProjectStore


class WorkbenchService:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def list_projects(self) -> list[OntologyProject]:
        projects = [self.store.load_project(project_id) for project_id in self.store.list_project_ids()]
        return sorted(projects, key=lambda project: project.updated_at, reverse=True)

    def create_project(self, name: str, description: str = "") -> OntologyProject:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name is required")

        project_id = self._next_available_id(self._slugify(clean_name), self.store.project_exists)
        project = OntologyProject(id=project_id, name=clean_name, description=description.strip())
        self.store.save_project(project)
        return project

    def get_project(self, project_id: str) -> OntologyProject:
        return self.store.load_project(project_id)

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

        seen_names: set[str] = set()
        for concept in project.concepts:
            normalized_name = concept.name.strip().lower()
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
    ) -> tuple[OntologyProject, dict[str, int]]:
        project = self.store.load_project(project_id)
        existing_concepts = [] if clear_existing else project.concepts
        existing_relations = [] if clear_existing else project.relations
        bundle = build_bim_import_bundle(
            payload,
            existing_concept_ids={concept.id for concept in existing_concepts},
            existing_relation_ids={relation.id for relation in existing_relations},
            slugify=self._slugify,
        )

        if project.concepts or project.relations or project.metadata:
            self.store.create_snapshot(project, note=snapshot_note.strip() or "before-bim-import")

        if clear_existing:
            project.concepts = []
            project.relations = []

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

    def execute_fabric_validation_query(self, query_name: str) -> dict[str, object]:
        return execute_fabric_read_only_query(query_name)

    def list_atlas_assessments(self, project_id: str) -> list[dict[str, object]]:
        return self.store.list_atlas_assessments(project_id)

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

    def create_nexo_draft(self, project_id: str, assessment_run_id: str) -> dict[str, object]:
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
            project, assessment, business_context, semantic_inventory, draft_id
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
    ) -> dict[str, object]:
        release = self.store.load_nexo_release(project_id, release_id)
        package_id = f"mapping-{target.strip().lower()}-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        package = build_publication_package(release, target, prepared_by, note, package_id)
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
        existing_ids = {concept.id for concept in project.concepts}
        added = 0
        for table in tables:
            schema = str(table.get("schema", "dbo"))
            name = str(table.get("name", "")).strip()
            if not name:
                continue
            concept_id = self._slugify(f"fabric-{schema}-{name}")
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
            if concept_id in existing_ids:
                continue
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
                    },
                )
            )
            existing_ids.add(concept_id)
            added += 1
        package_path = Path(str(discovery.get("package_path", "")))
        source_path = package_path / "metadata_inventory.json"
        project.metadata.update(
            {
                "source.format": "fabric-information-schema",
                "source.technical.path": str(source_path),
                "source.technical.filename": "metadata_inventory.json",
                "source.technical.sha256": self._file_sha256(source_path),
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
        release = next((item for item in self.store.list_nexo_releases(project_id) if item.get("release_id") == release_id), None)
        if release is None:
            raise FileNotFoundError(f"Nexo release not found: {release_id}")
        context_pack = json.loads((Path(str(release["package_path"])) / "agent_context_pack.json").read_text(encoding="utf-8"))
        investigation_id = f"argos-{utc_now_iso().replace(':', '-').replace('+', '-')}-{uuid.uuid4().hex[:12]}"
        investigation = investigate_context_pack(context_pack, question.strip(), investigation_id)
        query_name = select_fabric_query(question)
        if query_name and _has_fabric_query_binding(context_pack, query_name):
            query_result = self.execute_fabric_validation_query(query_name)
            investigation["live_query"] = query_result
            investigation["manifest"]["mode"] = "deterministic-context-pack-plus-fabric-read-only"
            investigation["answer"] = _format_fabric_query_answer(query_name, query_result)
            investigation["manifest"]["status"] = "answered"
        investigation["package_path"] = str(self.store.save_runtime_investigation(project_id, investigation))
        return investigation

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
        evaluation = evaluate_context_pack(context_pack, cases, evaluation_id)
        evaluation["package_path"] = str(self.store.save_runtime_evaluation(project_id, evaluation))
        return evaluation

    def _load_release_context_pack(self, project_id: str, release_id: str) -> dict[str, object]:
        release = self.store.load_nexo_release(project_id, release_id)
        return json.loads((Path(str(release["package_path"])) / "agent_context_pack.json").read_text(encoding="utf-8"))

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


def _has_fabric_query_binding(context_pack: dict[str, object], query_name: str) -> bool:
    required_table = FABRIC_QUERY_BINDING_TABLES.get(query_name)
    if not required_table:
        return False
    return any(
        required_table in str(binding.get("name", ""))
        for binding in context_pack.get("data_bindings", [])
        if isinstance(binding, dict)
    )
