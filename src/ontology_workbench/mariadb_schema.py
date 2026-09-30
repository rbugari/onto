from __future__ import annotations

import re
from pathlib import Path


_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`(?P<table>[^`]+)`\s*\("
    r"(?P<body>.*?)\n\)\s*(?:ENGINE|;)",
    re.IGNORECASE | re.DOTALL,
)
_COLUMN_RE = re.compile(r"^`(?P<name>[^`]+)`\s+(?P<data_type>[A-Za-z]+(?:\([^)]*\))?)", re.IGNORECASE)
_FOREIGN_KEY_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(`(?P<from_column>[^`]+)`\)\s+"
    r"REFERENCES\s+`(?P<to_table>[^`]+)`\s*\(`(?P<to_column>[^`]+)`\)",
    re.IGNORECASE,
)


class MariaDBSchemaError(ValueError):
    """Controlled error for invalid or unsupported MariaDB schema dumps."""


def parse_mariadb_schema_dump(path: Path) -> dict[str, object]:
    """Extract tables, columns and declared foreign keys without reading INSERT rows."""
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"No se encontro el dump MariaDB: {source}")

    text = source.read_text(encoding="utf-8", errors="replace")
    tables: list[dict[str, object]] = []
    relationships: list[dict[str, object]] = []
    for table_match in _CREATE_TABLE_RE.finditer(text):
        table_name = table_match.group("table")
        columns: list[dict[str, str]] = []
        for raw_line in table_match.group("body").splitlines():
            line = raw_line.strip().rstrip(",")
            column_match = _COLUMN_RE.match(line)
            if column_match:
                columns.append(
                    {
                        "name": column_match.group("name"),
                        "dataType": column_match.group("data_type"),
                    }
                )
            foreign_key_match = _FOREIGN_KEY_RE.search(line)
            if foreign_key_match:
                relationships.append(
                    {
                        "fromTable": table_name,
                        "fromColumn": foreign_key_match.group("from_column"),
                        "toTable": foreign_key_match.group("to_table"),
                        "toColumn": foreign_key_match.group("to_column"),
                        "isActive": True,
                    }
                )
        if columns:
            tables.append({"name": table_name, "columns": columns})

    if not tables:
        raise MariaDBSchemaError("No se encontraron CREATE TABLE con columnas en el dump")
    return {
        "model": {
            "culture": "",
            "tables": tables,
            "relationships": relationships,
        },
        "source_format": "mariadb-schema",
        "table_count": len(tables),
        "column_count": sum(len(table["columns"]) for table in tables),
        "relationship_count": len(relationships),
    }
