from __future__ import annotations

import hashlib
import json

from ontology_workbench.models import OntologyProject


SCOPE_KEY = "atlas.explanatory_scope_decisions"
ASPECTS = {
    "entity": ["significado", "granularidad", "identificacion"],
    "relationship": ["extremos", "significado", "cardinalidad_si_aplica"],
    "kpi": ["definicion", "formula", "granularidad", "filtros_y_exclusiones"],
    "property": ["significado", "tipo", "valores_o_unidad"],
}


def build_explanatory_scope(project: OntologyProject) -> dict[str, object]:
    decisions = json.loads(project.metadata.get(SCOPE_KEY, "{}"))
    sources = {source.source_id: source for source in project.sources}
    elements = {}
    object_keys = {}

    def add(kind, name, source_ids, reference, origin_ids, default_reason=""):
        source_names = sorted(
            f"{sources[source_id].platform}:{sources[source_id].name}"
            if source_id in sources else "unassigned"
            for source_id in source_ids
        )
        logical_key = json.dumps([kind, source_names, reference], ensure_ascii=True)
        element_id = hashlib.sha256(logical_key.encode()).hexdigest()[:24]
        decision = decisions.get(element_id, {})
        included = decision.get("included", not default_reason)
        reason = str(decision.get("reason", default_reason))
        if not included and not reason.strip():
            raise ValueError("Cada exclusion del universo necesita un motivo.")
        use_cases = [case.use_case_id for case in project.use_cases if set(case.source_ids) & set(source_ids)]
        if element_id in elements:
            elements[element_id]["origin_ids"].extend(origin_ids)
        else:
            elements[element_id] = {
                "element_id": element_id, "kind": kind, "name": name,
                "source_ids": source_ids, "source_names": source_names,
                "technical_reference": reference, "origin_ids": origin_ids,
                "use_case_ids": use_cases, "use_case_link_basis": "source_scope_only",
                "required_aspects": ASPECTS[kind], "included": included,
                "scope_reason": reason, "evaluation_status": "not_evaluated",
            }
        return element_id

    for concept in project.concepts:
        metadata = concept.metadata
        object_type = metadata.get("bim.objectType") or metadata.get("fabric.objectType")
        object_type = object_type or next((tag for tag in concept.tags if tag in ("table", "column", "measure")), "concept")
        kind = {"column": "property", "measure": "kpi"}.get(object_type.lower(), "entity")
        source_id = metadata.get("source.id", "")
        reference = [metadata.get("bim.table") or metadata.get("fabric.table") or concept.name,
                     metadata.get("bim.column") or metadata.get("bim.measure") or concept.name]
        object_keys[concept.id] = add(kind, concept.name, [source_id], reference, [concept.id])

    for relation in project.relations:
        endpoints = [object_keys.get(relation.source_id), object_keys.get(relation.target_id)]
        source_ids = sorted({source_id for endpoint in endpoints if endpoint in elements
                             for source_id in elements[endpoint]["source_ids"]})
        property_link = relation.relation_type in ("contains-column", "contains-measure")
        add("relationship", relation.relation_type, source_ids,
            [*endpoints, relation.relation_type], [relation.id],
            "Vinculo estructural de propiedades; se evalua con la propiedad." if property_link else "")

    rows = sorted(elements.values(), key=lambda item: (item["kind"], item["name"], item["element_id"]))
    groups = {kind: {"total": sum(row["kind"] == kind for row in rows),
                     "included": sum(row["kind"] == kind and row["included"] for row in rows)}
              for kind in ASPECTS}
    missing_sources = [source.source_id for source in project.sources if source.status != "inventoried"]
    limitations = []
    if missing_sources:
        limitations.append("Hay sistemas declarados sin metadata; el universo disponible es incompleto.")
    if not project.concepts:
        limitations.append("Sin inventario tecnico: universo provisional, no se puede medir todo el dominio.")
    if any("" in row["source_ids"] for row in rows):
        limitations.append("Hay elementos sin sistema identificado; se conservan en el universo pendiente de asignacion.")
    if any(not case.source_ids for case in project.use_cases):
        limitations.append("Hay casos de uso sin sistemas vinculados.")
    if any(not row["use_case_ids"] and row["included"] for row in rows):
        limitations.append("Hay elementos sin caso de uso vinculado; se conservan como pendientes.")
    snapshot = [(row["element_id"], row["included"], row["scope_reason"], row["use_case_ids"]) for row in rows]
    version = hashlib.sha256(json.dumps([snapshot, sorted(missing_sources), ASPECTS], sort_keys=True).encode()).hexdigest()[:24]
    return {
        "format": "atlas-explanatory-scope-v1", "criteria_version": "explanatory-aspects-v1",
        "scope_version": version, "elements": rows, "groups": groups,
        "missing_source_ids": missing_sources, "limitations": limitations,
        "pending_decision_ids": sorted(set(decisions) - set(elements)),
        "use_case_link_warning": "Los vinculos por sistema indican alcance, no relevancia semantica confirmada.",
    }