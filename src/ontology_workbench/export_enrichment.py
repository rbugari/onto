"""Content derived from approved evidence to fill the platform packages (types, joins, KPI formulas, Page sections).

Everything here is deterministic and only uses what the release already carries; nothing is invented.
Items that need a person (SQL for a KPI, ids of the platform) stay as placeholders.
"""
from __future__ import annotations

import re

from ontology_workbench.cross_source import key_signature, normalize_entity

_TYPE_TOKENS = {
    "Boolean": {"bool", "boolean", "bit"},
    "DateTime": {"date", "datetime", "datetime2", "smalldatetime", "datetimeoffset", "timestamp", "timestamp_ntz", "time"},
    "BigInt": {"int", "integer", "int64", "bigint", "smallint", "tinyint", "mediumint", "long", "short", "byte", "serial"},
    "Double": {"double", "float", "float64", "real", "decimal", "numeric", "number", "money", "smallmoney", "currency"},
    "String": {"varchar", "char", "text", "string", "nvarchar", "nchar", "longtext", "mediumtext", "tinytext", "enum", "uuid"},
}
_TOKEN_TYPE = {token: value_type for value_type, tokens in _TYPE_TOKENS.items() for token in tokens}
MAX_USAGE_ITEMS = 5


def fabric_value_type(data_type: str) -> str | None:
    """Fabric ontology value type for a SQL/BIM data type, or None when it is not recognised."""
    base = re.split(r"[(\s<]", data_type.strip().lower())[0]
    return _TOKEN_TYPE.get(base)


def column_index(model) -> dict[str, dict[str, tuple[str, str]]]:
    """table -> {normalized column name: (column name, data type)} from the approved column assets."""
    index: dict[str, dict[str, tuple[str, str]]] = {}
    for asset in model.assets:
        if model.asset_kind(asset) != "column":
            continue
        metadata = dict(asset.get("technical_metadata", {}))
        name = str(metadata.get("fabric.column") or str(asset["name"]).split("[")[-1].rstrip("]").split(".")[-1])
        data_type = str(metadata.get("fabric.dataType") or metadata.get("bim.dataType") or "")
        index.setdefault(model.asset_table(asset), {})[_norm(name)] = (name, data_type)
    return index


def concept_tables(model) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    for _binding, business, asset in model.binding_pairs():
        table = model.asset_table(asset)
        if table not in tables.setdefault(str(business["id"]), []):
            tables[str(business["id"])].append(table)
    return tables


def property_column(model, concept_id: str, property_name: str, index, tables) -> tuple[str, str, str] | None:
    """(table, column, data type) of the bound column that matches a property by name."""
    wanted = _norm(property_name)
    for table in tables.get(concept_id, []):
        found = index.get(table, {}).get(wanted)
        if found:
            return table, found[0], found[1]
    return None


def relationship_joins(model, index, tables) -> list[dict[str, str]]:
    """Joins between the tables of two related concepts, when a key column in the release proves the link."""
    joins = []
    for relation in model.relationships:
        linked = [str(item) for item in relation.get("linked_candidate_ids", [])]
        if len(linked) != 2 or not all(tables.get(item) for item in linked):
            continue
        for first, second in ((linked[0], linked[1]), (linked[1], linked[0])):
            join = _join(tables[first][0], tables[second][0], index)
            if join:
                joins.append({**join, "relationship": str(relation["name"])})
                break
    return joins


def kpi_formula(model, kpi_id: str) -> str:
    """DAX expression of a measure bound to the KPI (Power BI semantic models), if the release carries one."""
    for _binding, business, asset in model.binding_pairs():
        if str(business["id"]) == kpi_id:
            expression = str(dict(asset.get("technical_metadata", {})).get("bim.expression", "")).strip()
            if expression:
                return " ".join(expression.split())
    return ""


def page_sections(model, item: dict[str, object], example_questions: list[str]) -> dict[str, list[str]]:
    """Business usage (rules and KPIs that mention the item) and example questions that name it."""
    name = str(item["name"]).casefold()
    usage = [
        f"{kind}: **{other['name']}** - {' '.join(str(other['definition']).split())[:240]}"
        for kind, others in (("Regla", model.rules), ("KPI", model.kpis))
        for other in others
        if other["id"] != item["id"] and name in str(other["definition"]).casefold()
    ][:MAX_USAGE_ITEMS]
    examples = [question for question in example_questions if name in question.casefold()][:MAX_USAGE_ITEMS]
    return {"usage": usage, "examples": examples}


def item_owner(model, item_id: str) -> str:
    for collection in (model.properties, model.relationships, model.synonyms, model.constraints, model.bindings):
        for element in collection:
            if item_id in element.get("linked_candidate_ids", []) and str(element.get("owner", "")).strip():
                return str(element["owner"]).strip()
    return ""


def placeholder_counts(files: dict[str, str]) -> dict[str, int]:
    return {path: text.count("COMPLETAR") for path, text in sorted(files.items()) if "COMPLETAR" in text}


def _join(many_table: str, one_table: str, index) -> dict[str, str] | None:
    many_columns, one_columns = index.get(many_table, {}), index.get(one_table, {})
    one_entity, many_entity = normalize_entity(one_table), normalize_entity(many_table)
    reference = next(
        (name for name, _ in many_columns.values() if key_signature(name, many_entity) == f"{one_entity}#id" and one_entity != many_entity),
        None,
    )
    key = next((name for name, _ in one_columns.values() if key_signature(name, one_entity) == f"{one_entity}#id"), None)
    if not reference or not key:
        return None
    return {"left_table": many_table, "left_column": reference, "right_table": one_table, "right_column": key}


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())
