"""Parsers for metadata exported outside ONTO (Databricks, SQL Server, Postgres, Snowflake...).

Only structure is read: DDL statements or information_schema column exports. Data rows are ignored.
"""
from __future__ import annotations

import csv
import io
import re


_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:(?:EXTERNAL|TEMPORARY|TEMP|TRANSIENT|STREAMING)\s+)*"
    r"(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>[`\"\[\]\w.$-]+)\s*\(",
    re.IGNORECASE,
)
_CONSTRAINT_RE = re.compile(
    r"^(primary\s+key|foreign\s+key|constraint\s|unique[\s(]|(unique\s+)?key[\s(`]|index[\s(`]|"
    r"check[\s(]|fulltext\s|spatial\s|period\s+for)",
    re.IGNORECASE,
)
_FOREIGN_KEY_RE = re.compile(
    r"FOREIGN\s+KEY\s*\((?P<from_column>[^)]+)\)\s*REFERENCES\s+(?P<to_table>[`\"\[\]\w.$-]+)\s*"
    r"\((?P<to_column>[^)]+)\)",
    re.IGNORECASE,
)
_INLINE_REFERENCE_RE = re.compile(
    r"REFERENCES\s+(?P<to_table>[`\"\[\]\w.$-]+)\s*\((?P<to_column>[^)]+)\)", re.IGNORECASE
)
_COLUMN_HEADERS = {
    "catalog": ("table_catalog", "catalog", "catalog_name", "database", "table_cat"),
    "schema": ("table_schema", "schema", "schema_name", "owner", "table_schem"),
    "table": ("table_name", "table", "tabla", "object_name"),
    "column": ("column_name", "column", "columna", "field", "col_name"),
    "data_type": ("data_type", "type", "type_name", "full_data_type", "tipo"),
}


def parse_sql_ddl(text: str) -> dict[str, object]:
    """Extract tables, columns and declared foreign keys from generic CREATE TABLE statements."""
    tables: list[dict[str, object]] = []
    relationships: list[dict[str, object]] = []
    clean_text = _strip_sql_comments(text)
    for match in _CREATE_TABLE_RE.finditer(clean_text):
        table_name = _clean_qualified_name(match.group("name"))
        body = _balanced_body(clean_text, match.end() - 1)
        if body is None:
            continue
        columns: list[dict[str, str]] = []
        for item in _split_top_level(body):
            foreign_key = _FOREIGN_KEY_RE.search(item)
            if foreign_key:
                for from_column, to_column in zip(
                    _identifier_list(foreign_key.group("from_column")),
                    _identifier_list(foreign_key.group("to_column")),
                ):
                    relationships.append(
                        _relationship(table_name, from_column, foreign_key.group("to_table"), to_column)
                    )
                continue
            if _CONSTRAINT_RE.match(item):
                continue
            column = _column_definition(item)
            if column is None:
                continue
            columns.append(column)
            inline_reference = _INLINE_REFERENCE_RE.search(item)
            if inline_reference:
                to_column = _identifier_list(inline_reference.group("to_column"))[0]
                relationships.append(
                    _relationship(table_name, column["name"], inline_reference.group("to_table"), to_column)
                )
        if columns:
            tables.append({"name": table_name, "columns": columns})
    if not tables:
        raise ValueError("No se encontraron sentencias CREATE TABLE con columnas en el archivo")
    return _model_payload(tables, relationships, "sql-ddl")


def parse_columns_csv(text: str) -> dict[str, object]:
    """Read an information_schema.columns style export (one row per column)."""
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = {(header or "").strip().casefold(): header for header in reader.fieldnames or []}
    resolved = {
        key: next((headers[name] for name in names if name in headers), None)
        for key, names in _COLUMN_HEADERS.items()
    }
    if not resolved["table"] or not resolved["column"]:
        raise ValueError(
            "El CSV debe tener al menos las columnas table_name y column_name "
            "(formato information_schema.columns)"
        )
    tables: dict[str, dict[str, object]] = {}
    for row in reader:
        table = str(row.get(resolved["table"]) or "").strip()
        column = str(row.get(resolved["column"]) or "").strip()
        if not table or not column:
            continue
        schema = str(row.get(resolved["schema"]) or "").strip() if resolved["schema"] else ""
        table_name = f"{schema}.{table}" if schema else table
        entry = tables.setdefault(table_name, {"name": table_name, "columns": []})
        entry["columns"].append(
            {
                "name": column,
                "dataType": str(row.get(resolved["data_type"]) or "unknown").strip()
                if resolved["data_type"]
                else "unknown",
            }
        )
    if not tables:
        raise ValueError("El CSV no contiene filas con tabla y columna")
    return _model_payload(list(tables.values()), [], "columns-csv")


def _model_payload(
    tables: list[dict[str, object]], relationships: list[dict[str, object]], source_format: str
) -> dict[str, object]:
    return {
        "model": {"culture": "", "tables": tables, "relationships": relationships},
        "source_format": source_format,
        "table_count": len(tables),
        "column_count": sum(len(table["columns"]) for table in tables),
        "relationship_count": len(relationships),
    }


def _relationship(from_table: str, from_column: str, to_table: str, to_column: str) -> dict[str, object]:
    return {
        "fromTable": from_table,
        "fromColumn": _clean_identifier(from_column),
        "toTable": _clean_qualified_name(to_table),
        "toColumn": _clean_identifier(to_column),
        "isActive": True,
    }


def _column_definition(item: str) -> dict[str, str] | None:
    match = re.match(r"^(`[^`]+`|\"[^\"]+\"|\[[^\]]+\]|[\w$]+)\s+(?P<type>[A-Za-z][\w ]*?(?:\([^)]*\)|<.*>)?)(?:\s|$)", item.strip())
    if not match:
        return None
    return {"name": _clean_identifier(match.group(1)), "dataType": match.group("type").strip()}


def _balanced_body(text: str, open_index: int) -> str | None:
    depth = 0
    for index in range(open_index, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[open_index + 1:index]
    return None


def _split_top_level(body: str) -> list[str]:
    items: list[str] = []
    depth = 0
    current: list[str] = []
    for char in body:
        if char in "(<":
            depth += 1
        elif char in ")>":
            depth -= 1
        if char == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if "".join(current).strip():
        items.append("".join(current).strip())
    return [item for item in items if item]


def _strip_sql_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", text)


def _identifier_list(value: str) -> list[str]:
    return [_clean_identifier(part) for part in value.split(",") if part.strip()]


def _clean_identifier(value: str) -> str:
    return value.strip().strip("`\"[]")


def _clean_qualified_name(value: str) -> str:
    return ".".join(_clean_identifier(part) for part in value.split(".") if part.strip("`\"[] "))
