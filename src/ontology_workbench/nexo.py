from __future__ import annotations

from collections import Counter

from ontology_workbench.models import OntologyProject, utc_now_iso


NEXO_PRODUCT_NAME = "Nexo"
NEXO_DRAFT_FORMAT_VERSION = "nexo-registry-draft-v0.2"
NEXO_RELEASE_FORMAT_VERSION = "nexo-ontology-release-v0.2"
MODEL_ELEMENT_TYPES = {"property", "relationship", "synonym", "constraint", "source_binding"}


def build_registry_draft(
    project: OntologyProject,
    assessment_manifest: dict[str, object],
    business_context: dict[str, object],
    semantic_inventory: dict[str, object],
    draft_id: str,
) -> dict[str, object]:
    """Materialize reviewable registry candidates from an Atlas assessment package."""
    candidates: list[dict[str, object]] = []
    _add_context_candidates(candidates, business_context.get("definitions", []), "concept")
    _add_context_candidates(candidates, business_context.get("business_rules", []), "business_rule")
    _add_context_candidates(candidates, business_context.get("kpis", []), "kpi")
    _add_technical_candidates(candidates, semantic_inventory.get("objects", []))
    counts = Counter(str(candidate["candidate_type"]) for candidate in candidates)
    manifest = {
        "format": NEXO_DRAFT_FORMAT_VERSION,
        "product": NEXO_PRODUCT_NAME,
        "draft_id": draft_id,
        "created_at": utc_now_iso(),
        "project_id": project.id,
        "project_name": project.name,
        "source_assessment": {
            "run_id": assessment_manifest["run_id"],
            "created_at": assessment_manifest["created_at"],
            "scope": assessment_manifest["scope"],
        },
        "candidate_summary": {
            "total": len(candidates),
            "pending_review": len(candidates),
            "approved": 0,
            "rejected": 0,
            **dict(counts),
        },
        "model_element_summary": model_element_summary([]),
        "warning": (
            "Un draft Nexo contiene candidatos y elementos de modelo pendientes. "
            "No es una ontologia aprobada ni un paquete publicable."
        ),
    }
    return {
        "manifest": manifest,
        "candidates": candidates,
        "review_decisions": [],
        "model_elements": [],
        "model_element_decisions": [],
    }


def refresh_candidate_summary(draft: dict[str, object]) -> dict[str, int]:
    candidates = list(draft["candidates"])
    type_counts = Counter(str(candidate["candidate_type"]) for candidate in candidates)
    status_counts = Counter(str(candidate["status"]) for candidate in candidates)
    return {
        "total": len(candidates),
        "pending_review": status_counts["pending_review"],
        "approved": status_counts["approved"],
        "rejected": status_counts["rejected"],
        **dict(type_counts),
    }


def model_element_summary(elements: list[dict[str, object]]) -> dict[str, int]:
    status_counts = Counter(str(element.get("status", "pending_review")) for element in elements)
    type_counts = Counter(str(element.get("element_type", "unknown")) for element in elements)
    return {
        "total": len(elements),
        "pending_review": status_counts["pending_review"],
        "approved": status_counts["approved"],
        "rejected": status_counts["rejected"],
        **dict(type_counts),
    }


def build_model_element(
    element_id: str,
    element_type: str,
    name: str,
    definition: str,
    owner: str,
    linked_candidate_ids: list[str],
) -> dict[str, object]:
    """Create a manually curated, reviewable structure for the canonical model."""
    clean_type = element_type.strip().lower()
    clean_links = list(dict.fromkeys(item.strip() for item in linked_candidate_ids if item.strip()))
    if clean_type not in MODEL_ELEMENT_TYPES:
        raise ValueError("Tipo de elemento canónico no soportado")
    if not name.strip() or not definition.strip():
        raise ValueError("Nombre y definición son obligatorios para un elemento canónico")
    expected_links = 2 if clean_type in {"relationship", "source_binding"} else 1
    if len(clean_links) != expected_links:
        raise ValueError(
            "Una relación o source binding requiere exactamente dos candidatos vinculados; los demás elementos requieren uno"
        )
    return {
        "element_id": element_id,
        "element_type": clean_type,
        "name": name.strip(),
        "definition": definition.strip(),
        "owner": owner.strip(),
        "linked_candidate_ids": clean_links,
        "status": "pending_review",
        "created_at": utc_now_iso(),
        "decision": None,
    }


def build_ontology_release(
    draft: dict[str, object], release_id: str, released_by: str, release_note: str
) -> dict[str, object]:
    candidates = list(draft["candidates"])
    pending = [candidate for candidate in candidates if candidate["status"] == "pending_review"]
    if pending:
        raise ValueError("No se puede emitir una release mientras existan candidatos pending_review")
    approved = [candidate for candidate in candidates if candidate["status"] == "approved"]
    if not approved:
        raise ValueError("No se puede emitir una release sin candidatos aprobados")

    model_elements = list(draft.get("model_elements", []))
    pending_model_elements = [
        element for element in model_elements if element.get("status") == "pending_review"
    ]
    if pending_model_elements:
        raise ValueError("No se puede emitir una release mientras existan elementos del modelo pendientes")
    approved_candidate_ids = {str(candidate["candidate_id"]) for candidate in approved}
    approved_model_elements = [
        element for element in model_elements if element.get("status") == "approved"
    ]
    invalid_bindings = [
        element
        for element in approved_model_elements
        if not set(map(str, element.get("linked_candidate_ids", []))).issubset(approved_candidate_ids)
    ]
    if invalid_bindings:
        raise ValueError(
            "Los elementos aprobados del modelo solo pueden vincular candidatos aprobados"
        )

    source_assessment = dict(dict(draft["manifest"])["source_assessment"])
    canonical_concepts = [
        _canonical_candidate(candidate)
        for candidate in approved
        if candidate["candidate_type"] == "concept"
    ]
    technical_assets = [
        _canonical_candidate(candidate)
        for candidate in approved
        if candidate["candidate_type"] == "technical_asset"
    ]
    canonical_ontology = {
        "format": "nexo-canonical-ontology-v0.2",
        "project_id": dict(draft["manifest"])["project_id"],
        "entities": canonical_concepts,
        "concepts": canonical_concepts,
        "business_rules": [
            _canonical_candidate(candidate)
            for candidate in approved
            if candidate["candidate_type"] == "business_rule"
        ],
        "kpis": [
            _canonical_candidate(candidate)
            for candidate in approved
            if candidate["candidate_type"] == "kpi"
        ],
        "technical_assets": technical_assets,
        "properties": _canonical_model_elements(approved_model_elements, "property"),
        "relationships": _canonical_model_elements(approved_model_elements, "relationship"),
        "synonyms": _canonical_model_elements(approved_model_elements, "synonym"),
        "constraints": _canonical_model_elements(approved_model_elements, "constraint"),
        "data_bindings": _canonical_model_elements(approved_model_elements, "source_binding"),
        "ownership": _ownership(approved_model_elements),
        "warning": (
            "Las relaciones y restricciones solo aparecen cuando una persona las agrega y aprueba explicitamente."
        ),
    }
    source_bindings = [
        {
            "candidate_id": candidate["candidate_id"],
            "source_document_id": candidate["evidence"]["source_document_id"],
            "source_chunk_id": candidate["evidence"]["source_chunk_id"],
        }
        for candidate in approved
    ] + [
        {
            "model_element_id": element["element_id"],
            "linked_candidate_ids": list(element.get("linked_candidate_ids", [])),
        }
        for element in approved_model_elements
    ]
    evidence_index = {
        "items": [
            {"candidate_id": candidate["candidate_id"], **dict(candidate["evidence"])}
            for candidate in approved
        ] + [
            {
                "model_element_id": element["element_id"],
                "linked_candidate_ids": list(element.get("linked_candidate_ids", [])),
                "owner": element.get("owner", ""),
            }
            for element in approved_model_elements
        ]
    }
    agent_context_pack = {
        "format": "nexo-agent-context-pack-v0.2",
        "release_id": release_id,
        "project_id": dict(draft["manifest"])["project_id"],
        "scope": source_assessment["scope"],
        "concepts": canonical_ontology["concepts"],
        "business_rules": canonical_ontology["business_rules"],
        "kpis": canonical_ontology["kpis"],
        "properties": canonical_ontology["properties"],
        "relationships": canonical_ontology["relationships"],
        "synonyms": canonical_ontology["synonyms"],
        "constraints": canonical_ontology["constraints"],
        "technical_assets": canonical_ontology["technical_assets"],
        "data_bindings": canonical_ontology["data_bindings"],
        "query_contract": {
            "mode": "fabric-read-only-bound-only",
            "allowed_operations": ["SELECT"],
            "requires_approved_data_binding": True,
            "disallowed_operations": ["INSERT", "UPDATE", "DELETE", "DDL", "arbitrary_sql"],
        },
        "usage_boundary": "Solo usar los elementos aprobados y sus source bindings; abstenerse fuera de esta evidencia.",
    }
    return {
        "manifest": {
            "format": NEXO_RELEASE_FORMAT_VERSION,
            "product": NEXO_PRODUCT_NAME,
            "release_id": release_id,
            "draft_id": dict(draft["manifest"])["draft_id"],
            "project_id": dict(draft["manifest"])["project_id"],
            "created_at": utc_now_iso(),
            "released_by": released_by,
            "release_note": release_note,
            "source_assessment": source_assessment,
            "approved_candidates": len(approved),
            "rejected_candidates": len(candidates) - len(approved),
            "approved_model_elements": len(approved_model_elements),
            "rejected_model_elements": len(model_elements) - len(approved_model_elements),
        },
        "canonical_ontology": canonical_ontology,
        "review_decisions": list(draft["review_decisions"])
        + list(draft.get("model_element_decisions", [])),
        "evidence_index": evidence_index,
        "source_bindings": source_bindings,
        "agent_context_pack": agent_context_pack,
        "interoperability_mappings": [],
    }


def _add_context_candidates(
    candidates: list[dict[str, object]], items: object, candidate_type: str
) -> None:
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        name = str(item.get("term", "")).strip() or _short_name(text)
        definition = str(item.get("definition", "")).strip() or text
        if not name or not definition:
            continue
        candidates.append(
            {
                "candidate_id": f"candidate-{candidate_type}-{len(candidates) + 1:04d}",
                "candidate_type": candidate_type,
                "name": name,
                "definition": definition,
                "status": "pending_review",
                "confidence": float(item.get("confidence", 0)),
                "origin": "atlas-business-context",
                "evidence": {
                    "source_document_id": str(item.get("source_document_id", "")),
                    "source_chunk_id": str(item.get("source_chunk_id", "")),
                    "source_excerpt": str(item.get("source_excerpt", "")),
                    "evidence_status": str(item.get("evidence_status", "missing")),
                },
                "decision": None,
            }
        )


def _add_technical_candidates(candidates: list[dict[str, object]], objects: object) -> None:
    if not isinstance(objects, list):
        return
    for item in objects:
        if not isinstance(item, dict):
            continue
        metadata = dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {}
        if not str(metadata.get("fabric.objectType", "")).strip():
            continue
        name = str(item.get("name", "")).strip()
        source_ref = str(item.get("source_ref", name)).strip()
        if not name:
            continue
        candidates.append(
            {
                "candidate_id": f"candidate-technical-asset-{len(candidates) + 1:04d}",
                "candidate_type": "technical_asset",
                "name": name,
                "definition": f"Activo técnico Fabric {metadata.get('fabric.objectType')}: {source_ref}",
                "status": "pending_review",
                "confidence": 1.0,
                "origin": "atlas-fabric-metadata",
                "technical_metadata": metadata,
                "evidence": {
                    "source_document_id": "fabric-information-schema",
                    "source_chunk_id": f"fabric:{source_ref}",
                    "source_excerpt": source_ref,
                    "evidence_status": "available",
                },
                "decision": None,
            }
        )


def _short_name(text: str) -> str:
    return " ".join(text.split())[:120]


def _canonical_candidate(candidate: dict[str, object]) -> dict[str, object]:
    canonical = {
        "id": candidate["candidate_id"],
        "name": candidate["name"],
        "definition": candidate["definition"],
        "confidence": candidate["confidence"],
        "source_binding": {
            "source_document_id": candidate["evidence"]["source_document_id"],
            "source_chunk_id": candidate["evidence"]["source_chunk_id"],
        },
    }
    if candidate.get("technical_metadata"):
        canonical["technical_metadata"] = dict(candidate["technical_metadata"])
    return canonical


def _canonical_model_elements(
    elements: list[dict[str, object]], element_type: str
) -> list[dict[str, object]]:
    return [
        {
            "id": element["element_id"],
            "name": element["name"],
            "definition": element["definition"],
            "owner": element.get("owner", ""),
            "linked_candidate_ids": list(element.get("linked_candidate_ids", [])),
        }
        for element in elements
        if element.get("element_type") == element_type
    ]


def _ownership(elements: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {"element_id": element["element_id"], "owner": element["owner"]}
        for element in elements
        if str(element.get("owner", "")).strip()
    ]
