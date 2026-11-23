"""Atlas view of what the target platforms already understand and what stays without meaning.

Heuristic and deterministic: layers come from the system declaration or table names, reach from the platform
of each system, and "defined" from the terms the business-context scanner found. People confirm all of it.
"""
from __future__ import annotations

from collections import defaultdict

from ontology_workbench.cross_source import normalize_entity
from ontology_workbench.data_layers import LAYER_LABELS, table_layer
from ontology_workbench.platform_reach import BRIDGE_HINTS, PLATFORM_REACH, recommend_route, reachable

MAX_LISTED_ENTITIES = 8


def build_platform_coverage(
    technical_sources: list[dict[str, object]],
    objects: list[dict[str, object]],
    business_context: dict[str, object] | None,
) -> dict[str, object]:
    sources = {str(source["source_id"]): source for source in technical_sources}
    tables_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in objects:
        source_id = str(item.get("source_id") or "")
        if source_id not in sources or item.get("object_type") != "table":
            continue
        source = sources[source_id]
        name = str(item.get("name", ""))
        schema = str(dict(item.get("metadata", {})).get("fabric.schema", ""))
        full_name = f"{schema}.{name}" if schema and "." not in name else name
        layer, layer_source = table_layer(str(source.get("layer", "")), str(source.get("platform", "")), full_name)
        tables_by_source[source_id].append({"name": name, "layer": layer, "layer_source": layer_source})

    source_rows = []
    for source_id, source in sources.items():
        tables = tables_by_source.get(source_id, [])
        platform = str(source.get("platform", ""))
        source_rows.append({
            "source_id": source_id,
            "name": source.get("name", source_id),
            "platform": platform,
            "platform_label": source.get("platform_label", platform),
            "tables": len(tables),
            "layers": _count(table["layer"] for table in tables),
            "layer_source": "declared" if source.get("layer") else "inferred",
            "reachable_by": {
                target: {"reachable": reachable(platform, target), "bridge": "" if reachable(platform, target) else BRIDGE_HINTS[target]}
                for target in PLATFORM_REACH
            },
        })

    entities = _entity_rows(tables_by_source, sources, business_context)
    definitions_available = bool(business_context) and business_context.get("status") not in {"invalidated", "not_available"}
    return {
        "method": "layer-and-reach-heuristic-v1",
        "warning": (
            "Capa y alcance por plataforma son heuristicas (declaracion del sistema, nombres de tablas y plataforma de origen). "
            "Las confirman los responsables de cada sistema."
        ),
        "summary": {
            "tables": sum(row["tables"] for row in source_rows),
            "layers": _count(table["layer"] for tables in tables_by_source.values() for table in tables),
            "entities": len(entities),
            "definitions_available": definitions_available,
        },
        "sources": source_rows,
        "routes": {target: _route(target, source_rows) for target in PLATFORM_REACH},
        "entities": entities,
        "undefined_entities": _undefined(entities) if definitions_available else {"below_gold": [], "other": []},
    }


def coverage_gap_texts(coverage: dict[str, object]) -> list[dict[str, str]]:
    """Gap descriptions derived from undefined entities; empty when no business context was scanned."""
    undefined = dict(coverage.get("undefined_entities", {}))
    gaps = []
    if undefined.get("below_gold"):
        gaps.append({
            "code": "entities-without-definition-below-gold", "severity": "medium",
            "message": f"Hay {len(undefined['below_gold'])} entidad(es) en Silver o Bronze sin definicion de negocio: {_listed(undefined['below_gold'])}.",
            "recommendation": "Documentar su significado y granularidad; las plataformas parten de Gold y no lo infieren desde capas inferiores.",
        })
    if undefined.get("other"):
        gaps.append({
            "code": "entities-without-definition", "severity": "low",
            "message": f"Hay {len(undefined['other'])} entidad(es) sin definicion de negocio en ninguna capa: {_listed(undefined['other'])}.",
            "recommendation": "Agregar su definicion al glosario o excluirlas del alcance con motivo.",
        })
    return gaps


def _entity_rows(tables_by_source, sources, business_context) -> list[dict[str, object]]:
    defined = _defined_entities(business_context)
    by_entity: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"layers": set(), "sources": set()})
    for source_id, tables in tables_by_source.items():
        for table in tables:
            entity = normalize_entity(table["name"])
            if entity:
                by_entity[entity]["layers"].add(table["layer"])
                by_entity[entity]["sources"].add(str(sources[source_id].get("name", source_id)))
    return [
        {
            "entity": entity,
            "layers": sorted(data["layers"]),
            "sources": sorted(data["sources"]),
            "defined": None if defined is None else entity in defined,
        }
        for entity, data in sorted(by_entity.items())
    ]


def _defined_entities(business_context: dict[str, object] | None) -> set[str] | None:
    if not business_context or business_context.get("status") in {"invalidated", "not_available"}:
        return None
    return {
        normalize_entity(str(item.get("term", "")))
        for item in business_context.get("definitions", [])
        if isinstance(item, dict)
    } - {""}


def _undefined(entities: list[dict[str, object]]) -> dict[str, list[str]]:
    below, other = [], []
    for row in entities:
        if row["defined"] is False:
            (below if {"bronze", "silver"} & set(row["layers"]) else other).append(str(row["entity"]))
    return {"below_gold": below, "other": other}


def _route(target: str, source_rows: list[dict[str, object]]) -> dict[str, object]:
    total = sum(int(row["tables"]) for row in source_rows)
    outside = sum(int(row["tables"]) for row in source_rows if not row["reachable_by"][target]["reachable"])
    if not total:
        return {"route": "", "reason": "Todavia no hay tablas inventariadas.", "tables_total": 0, "tables_outside": 0}
    route, reason = recommend_route(target, total, outside, total, outside)
    return {"route": route, "reason": reason, "tables_total": total, "tables_outside": outside}


def _count(layers) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for layer in layers:
        counts[layer] += 1
    return {layer: counts[layer] for layer in LAYER_LABELS if counts[layer]}


def _listed(entities: list[str]) -> str:
    shown = ", ".join(entities[:MAX_LISTED_ENTITIES])
    return shown + (f" y {len(entities) - MAX_LISTED_ENTITIES} mas" if len(entities) > MAX_LISTED_ENTITIES else "")
