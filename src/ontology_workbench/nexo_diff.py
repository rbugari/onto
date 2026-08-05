from __future__ import annotations

import re

from ontology_workbench.models import utc_now_iso


def compare_nexo_artifacts(
    baseline: dict[str, object], candidate: dict[str, object]
) -> dict[str, object]:
    """Compare a Nexo draft or release by semantic identity, not transient file IDs."""
    baseline_items = _artifact_items(baseline)
    candidate_items = _artifact_items(candidate)
    baseline_by_key = {_semantic_key(item): item for item in baseline_items}
    candidate_by_key = {_semantic_key(item): item for item in candidate_items}
    shared_keys = baseline_by_key.keys() & candidate_by_key.keys()
    added = [_public_item(candidate_by_key[key]) for key in sorted(candidate_by_key.keys() - baseline_by_key.keys())]
    removed = [_public_item(baseline_by_key[key]) for key in sorted(baseline_by_key.keys() - candidate_by_key.keys())]
    changed = [
        {
            "item_type": candidate_by_key[key]["item_type"],
            "name": candidate_by_key[key]["name"],
            "changes": _changes(baseline_by_key[key], candidate_by_key[key]),
            "before": _public_item(baseline_by_key[key]),
            "after": _public_item(candidate_by_key[key]),
        }
        for key in sorted(shared_keys)
        if _changes(baseline_by_key[key], candidate_by_key[key])
    ]
    unchanged = len(shared_keys) - len(changed)
    return {
        "format": "nexo-semantic-comparison-v0.1",
        "created_at": utc_now_iso(),
        "baseline": _artifact_reference(baseline),
        "candidate": _artifact_reference(candidate),
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": unchanged,
            "baseline_items": len(baseline_items),
            "candidate_items": len(candidate_items),
        },
        "added": added,
        "removed": removed,
        "changed": changed,
        "warning": (
            "La comparación identifica la misma intención por tipo y nombre normalizado. "
            "No aprueba ni modifica drafts, decisiones o releases."
        ),
    }


def _artifact_items(artifact: dict[str, object]) -> list[dict[str, object]]:
    kind = str(artifact["kind"])
    payload = dict(artifact["payload"])
    if kind == "draft":
        return _draft_items(payload)
    if kind == "release":
        return _release_items(payload)
    raise ValueError("Tipo de artefacto Nexo no soportado para comparar")


def _draft_items(draft: dict[str, object]) -> list[dict[str, object]]:
    candidate_items = [
        {
            "item_type": str(candidate["candidate_type"]),
            "name": str(candidate["name"]),
            "definition": str(candidate["definition"]),
            "status": str(candidate.get("status", "pending_review")),
            "owner": "",
            "links": [],
        }
        for candidate in draft.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    model_items = [
        {
            "item_type": str(element["element_type"]),
            "name": str(element["name"]),
            "definition": str(element["definition"]),
            "status": str(element.get("status", "pending_review")),
            "owner": str(element.get("owner", "")),
            "links": sorted(map(str, element.get("linked_candidate_ids", []))),
        }
        for element in draft.get("model_elements", [])
        if isinstance(element, dict)
    ]
    return candidate_items + model_items


def _release_items(release: dict[str, object]) -> list[dict[str, object]]:
    ontology = dict(release["canonical_ontology"])
    groups = (
        ("concept", "concepts"),
        ("business_rule", "business_rules"),
        ("kpi", "kpis"),
        ("property", "properties"),
        ("relationship", "relationships"),
        ("synonym", "synonyms"),
        ("constraint", "constraints"),
    )
    return [
        {
            "item_type": item_type,
            "name": str(item["name"]),
            "definition": str(item["definition"]),
            "status": "approved",
            "owner": str(item.get("owner", "")),
            "links": sorted(map(str, item.get("linked_candidate_ids", []))),
        }
        for item_type, group_key in groups
        for item in ontology.get(group_key, [])
        if isinstance(item, dict)
    ]


def _artifact_reference(artifact: dict[str, object]) -> dict[str, str]:
    payload = dict(artifact["payload"])
    manifest = dict(payload["manifest"])
    return {
        "kind": str(artifact["kind"]),
        "id": str(manifest.get("draft_id", manifest.get("release_id", ""))),
        "created_at": str(manifest.get("created_at", "")),
    }


def _semantic_key(item: dict[str, object]) -> str:
    return f"{item['item_type']}:{_normalize(str(item['name']))}"


def _changes(before: dict[str, object], after: dict[str, object]) -> list[str]:
    fields = ("definition", "status", "owner", "links")
    return [field for field in fields if before.get(field) != after.get(field)]


def _public_item(item: dict[str, object]) -> dict[str, object]:
    return {
        "item_type": item["item_type"],
        "name": item["name"],
        "definition": item["definition"],
        "status": item["status"],
        "owner": item["owner"],
        "links": item["links"],
    }


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())
