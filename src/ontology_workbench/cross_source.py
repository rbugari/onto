"""Deterministic cross-system alignment: which business entities appear in more than one source."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict


_TABLE_PREFIXES = ("dim", "fact", "fct", "tbl", "tb", "t", "vw", "v", "stg", "raw", "bronze", "silver", "gold", "mst", "dwh")
_KEY_TOKENS = {"id", "key", "codigo", "cod", "code", "nro", "numero", "num", "sk", "pk", "uuid"}
# Small bilingual vocabulary so English BI models align with Spanish operational systems.
_SYNONYMS = {
    "customer": "cliente", "client": "cliente", "account": "cuenta",
    "product": "producto", "item": "articulo", "sku": "articulo",
    "order": "pedido", "orden": "pedido", "sale": "venta", "sales": "venta",
    "invoice": "factura", "supplier": "proveedor", "vendor": "proveedor",
    "employee": "empleado", "branch": "sucursal", "store": "sucursal",
    "warehouse": "deposito", "stock": "stock", "inventory": "stock",
    "date": "fecha", "calendar": "fecha", "region": "zona", "zone": "zona",
    "payment": "pago", "category": "categoria", "price": "precio",
}


def build_cross_source_map(
    sources: list[dict[str, object]], objects: list[dict[str, object]]
) -> dict[str, object]:
    """Group tables by normalized entity across sources and look for shared key columns."""
    source_names = {str(source["source_id"]): str(source.get("name", source["source_id"])) for source in sources}
    tables_by_entity: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    table_entity: dict[tuple[str, str], str] = {}
    for item in objects:
        source_id = str(item.get("source_id") or "")
        if source_id not in source_names or item.get("object_type") != "table":
            continue
        table_name = str(item.get("name", ""))
        entity = normalize_entity(table_name)
        if not entity:
            continue
        tables_by_entity[entity][source_id].append(table_name)
        table_entity[(source_id, table_name)] = entity

    keys_by_entity: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    key_columns: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for item in objects:
        source_id = str(item.get("source_id") or "")
        if source_id not in source_names or item.get("object_type") != "column":
            continue
        metadata = dict(item.get("metadata", {}))
        table_name = str(metadata.get("bim.table") or metadata.get("fabric.table") or "")
        if metadata.get("fabric.schema") and table_name:
            table_name = f"{metadata['fabric.schema']}.{table_name}"
        entity = table_entity.get((source_id, table_name))
        column_name = _column_name(str(item.get("name", "")))
        signature = key_signature(column_name, entity or "")
        if entity and signature:
            keys_by_entity[entity][source_id].add(signature)
            key_columns[(entity, source_id, signature)].append(column_name)

    shared_entities = []
    single_source_entities = []
    for entity, by_source in sorted(tables_by_entity.items()):
        row = {
            "entity": entity,
            "source_ids": sorted(by_source),
            "sources": [source_names[source_id] for source_id in sorted(by_source)],
            "tables": {source_id: sorted(tables) for source_id, tables in sorted(by_source.items())},
        }
        if len(by_source) < 2:
            single_source_entities.append(row)
            continue
        signatures_per_source = [keys_by_entity[entity].get(source_id, set()) for source_id in by_source]
        common = set.intersection(*signatures_per_source) if signatures_per_source else set()
        entity_signature = f"{entity}#id"
        common_key = entity_signature if entity_signature in common else ""
        row["common_key"] = common_key
        row["key_columns"] = {
            source_id: key_columns.get((entity, source_id, common_key), []) for source_id in sorted(by_source)
        } if common_key else {}
        row["shared_reference_keys"] = sorted(common - {entity_signature})
        shared_entities.append(row)

    return {
        "method": "normalized-table-names-v1",
        "warning": (
            "Alineacion heuristica por nombres normalizados. Sirve para orientar la revision; "
            "las equivalencias deben confirmarlas los responsables de cada sistema."
        ),
        "summary": {
            "sources": len(source_names),
            "entities": len(tables_by_entity),
            "shared_entities": len(shared_entities),
            "shared_with_common_key": sum(bool(row.get("common_key")) for row in shared_entities),
            "single_source_entities": len(single_source_entities),
        },
        "shared_entities": shared_entities,
        "single_source_entities": single_source_entities,
    }


def normalize_entity(table_name: str) -> str:
    tokens = _tokens(table_name.split(".")[-1])
    while len(tokens) > 1 and tokens[0] in _TABLE_PREFIXES:
        tokens = tokens[1:]
    tokens = [_canonical(token) for token in tokens if token not in _KEY_TOKENS]
    return "_".join(token for token in tokens if token)


def key_signature(column_name: str, table_entity: str) -> str:
    tokens = _tokens(column_name)
    if not tokens or not any(token in _KEY_TOKENS for token in tokens):
        return ""
    entity_tokens = [_canonical(token) for token in tokens if token not in _KEY_TOKENS]
    entity = "_".join(entity_tokens) or table_entity
    return f"{entity}#id" if entity else ""


def _column_name(name: str) -> str:
    bracket = re.search(r"\[([^\]]+)\]$", name)
    if bracket:
        return bracket.group(1)
    return name.split(".")[-1]


def _tokens(value: str) -> list[str]:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", ascii_value)
    return [token for token in re.split(r"[^a-z0-9]+", spaced.casefold()) if token]


def _canonical(token: str) -> str:
    token = _SYNONYMS.get(token, token)
    singular = _singular(token)
    return _SYNONYMS.get(singular, singular)


def _singular(token: str) -> str:
    if len(token) > 4 and token.endswith("es") and token[-3] in "lrndz" and token[-4] in "aeiou":
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token
