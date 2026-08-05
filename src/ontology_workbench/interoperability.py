from __future__ import annotations

from ontology_workbench.models import utc_now_iso


TARGETS = {
    "fabric": {
        "label": "Microsoft Fabric",
        "scope": "Paquete de mapping para revisión; no publica ni modifica un workspace de Fabric.",
    },
    "databricks": {
        "label": "Databricks",
        "scope": "Paquete de mapping para revisión; no publica ni modifica un workspace de Databricks.",
    },
}


def build_publication_package(
    release: dict[str, object], target: str, prepared_by: str, note: str, package_id: str
) -> dict[str, object]:
    clean_target = target.strip().lower()
    if clean_target not in TARGETS:
        raise ValueError("Destino de interoperabilidad no soportado")
    if not prepared_by.strip():
        raise ValueError("Se requiere responsable del paquete de interoperabilidad")
    manifest = dict(release["manifest"])
    ontology = dict(release["canonical_ontology"])
    mappings = [
        _mapping(clean_target, source_type, item)
        for source_type, key in (
            ("entity", "entities"),
            ("business_rule", "business_rules"),
            ("kpi", "kpis"),
            ("property", "properties"),
            ("relationship", "relationships"),
            ("synonym", "synonyms"),
            ("constraint", "constraints"),
            ("technical_asset", "technical_assets"),
            ("data_binding", "data_bindings"),
        )
        for item in ontology.get(key, [])
        if isinstance(item, dict)
    ]
    return {
        "manifest": {
            "format": "onto-interoperability-package-v0.1",
            "package_id": package_id,
            "created_at": utc_now_iso(),
            "project_id": manifest["project_id"],
            "release_id": manifest["release_id"],
            "target": clean_target,
            "target_label": TARGETS[clean_target]["label"],
            "status": "ready_for_review",
            "prepared_by": prepared_by.strip(),
            "note": note.strip(),
            "source_release_format": manifest["format"],
            "publication_mode": "local_mapping_only",
            "rollback": "No se ejecutó publicación externa; descartar este paquete revierte la preparación.",
        },
        "mapping": {
            "source_model": "nexo-canonical-ontology",
            "target": clean_target,
            "mappings": mappings,
            "unmapped_items": [],
            "limitations": [
                TARGETS[clean_target]["scope"],
                "Las decisiones de autenticación, workspace, permisos y publicación real se definen en un adapter posterior.",
                "El paquete nunca transporta datos de negocio ni secretos.",
            ],
        },
        "deployment_manifest": {
            "operation": "review_only",
            "requires": ["release_inmutable", "mapping_aprobado", "identidad_autorizada", "destino_configurado"],
            "external_changes": [],
        },
    }


def _mapping(target: str, source_type: str, item: dict[str, object]) -> dict[str, object]:
    target_kinds = {
        "fabric": {
            "entity": "semantic_concept",
            "business_rule": "business_rule_annotation",
            "kpi": "semantic_kpi",
            "property": "semantic_property",
            "relationship": "semantic_relationship",
            "synonym": "business_synonym",
            "constraint": "governance_constraint",
            "technical_asset": "source_metadata_asset",
            "data_binding": "approved_source_binding",
        },
        "databricks": {
            "entity": "governed_concept",
            "business_rule": "governance_rule",
            "kpi": "metric_definition",
            "property": "concept_property",
            "relationship": "concept_relationship",
            "synonym": "business_synonym",
            "constraint": "data_constraint",
            "technical_asset": "source_metadata_asset",
            "data_binding": "approved_source_binding",
        },
    }
    return {
        "source_id": item.get("id", ""),
        "source_type": source_type,
        "source_name": item.get("name", ""),
        "target_object_kind": target_kinds[target][source_type],
        "target_name": item.get("name", ""),
        "definition": item.get("definition", ""),
        "owner": item.get("owner", ""),
        "linked_candidate_ids": item.get("linked_candidate_ids", []),
        "status": "unbound",
    }
