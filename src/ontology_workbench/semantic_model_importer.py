from __future__ import annotations

import io
import json
import re
import zipfile


class SemanticModelImportError(ValueError):
    """Raised when a TMDL or PBIP semantic model cannot be interpreted."""


def normalize_semantic_model_api_payload(payload: dict[str, object]) -> dict[str, object]:
    """Normalize an API response envelope to the canonical model.bim shape."""
    if not isinstance(payload, dict):
        raise SemanticModelImportError("La respuesta API debe ser un objeto JSON")

    model_payload = payload.get("model", payload.get("semanticModel", payload))
    if not isinstance(model_payload, dict):
        raise SemanticModelImportError("La respuesta API no contiene un modelo semantico")
    tables = model_payload.get("tables")
    if not isinstance(tables, list) or not tables:
        raise SemanticModelImportError(
            "La respuesta API no contiene una lista de tablas no vacia"
        )
    relationships = model_payload.get("relationships", [])
    if not isinstance(relationships, list):
        raise SemanticModelImportError("relationships debe ser una lista")
    return {"model": {**model_payload, "tables": tables, "relationships": relationships}}


def parse_tmdl_text(text: str) -> dict[str, object]:
    """Parse the structural TMDL subset needed for Atlas inventory creation."""
    model: dict[str, object] = {"tables": [], "relationships": []}
    tables = model["tables"]
    relationships = model["relationships"]
    if not isinstance(tables, list) or not isinstance(relationships, list):
        raise SemanticModelImportError("No se pudo inicializar el modelo TMDL")

    current_table: dict[str, object] | None = None
    current_column: dict[str, object] | None = None
    current_measure: dict[str, object] | None = None
    current_relationship: dict[str, str] | None = None
    in_model = False
    model_properties: dict[str, str] = {}

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())

        if indent == 0 and stripped.startswith("model "):
            current_table = None
            current_column = None
            current_measure = None
            current_relationship = None
            in_model = True
            continue
        if indent == 0 and stripped.startswith("table "):
            table_name = _clean_name(stripped[6:].strip())
            if table_name:
                current_table = {
                    "name": table_name,
                    "columns": [],
                    "measures": [],
                }
                tables.append(current_table)
            current_column = None
            current_measure = None
            current_relationship = None
            in_model = False
            continue
        if indent == 0 and stripped.startswith("relationship "):
            current_table = None
            current_column = None
            current_measure = None
            current_relationship = {}
            in_model = False
            relationships.append(current_relationship)
            continue

        if indent > 0 and stripped.startswith("column ") and current_table is not None:
            column_name = _clean_name(stripped[7:].strip())
            current_column = {"name": column_name}
            current_table["columns"].append(current_column)
            current_measure = None
            current_relationship = None
            continue
        if indent > 0 and stripped.startswith("measure ") and current_table is not None:
            measure_match = re.match(r"measure\s+(.+?)(?:\s*=\s*(.*))?$", stripped)
            if measure_match is None:
                continue
            current_measure = {"name": _clean_name(measure_match.group(1).strip())}
            expression = (measure_match.group(2) or "").strip()
            if expression:
                current_measure["expression"] = expression
            current_table["measures"].append(current_measure)
            current_column = None
            current_relationship = None
            continue

        key, value = _split_property(stripped)
        if not key:
            continue
        clean_value = _clean_value(value)
        if current_relationship is not None and indent > 0:
            current_relationship[key] = clean_value
        elif current_measure is not None and indent > 0:
            if key in {"formatString", "displayFolder", "description"}:
                current_measure[key if key != "formatString" else "formatString"] = clean_value
            elif key == "expression" and not current_measure.get("expression"):
                current_measure["expression"] = clean_value
        elif current_column is not None and indent > 0:
            if key in {"dataType", "formatString", "description", "isHidden"}:
                current_column[key] = clean_value
        elif current_table is not None and indent > 0:
            if key in {"isHidden", "description"}:
                current_table[key] = clean_value
        elif in_model and indent > 0:
            model_properties[key] = clean_value
        elif indent == 0:
            model_properties[key] = clean_value

    if not tables:
        raise SemanticModelImportError("TMDL invalido: no se encontraron tablas")

    for relationship in relationships:
        from_table, from_column = _split_reference(relationship.get("fromColumn", ""))
        to_table, to_column = _split_reference(relationship.get("toColumn", ""))
        relationship["fromTable"] = relationship.get("fromTable", from_table)
        relationship["fromColumn"] = relationship.get("fromColumnName", from_column)
        relationship["toTable"] = relationship.get("toTable", to_table)
        relationship["toColumn"] = relationship.get("toColumnName", to_column)

    model.update({key: value for key, value in model_properties.items() if key in {
        "culture", "defaultPowerBIDataSourceVersion", "sourceQueryCulture"
    }})
    return {"model": model}


def parse_pbip_zip(content: bytes) -> dict[str, object]:
    """Read TMDL files from a PBIP ZIP without extracting arbitrary paths."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise SemanticModelImportError("El paquete PBIP no es un ZIP valido") from exc

    tmdl_parts: list[str] = []
    total_size = 0
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if ".." in info.filename.replace("\\", "/").split("/"):
                raise SemanticModelImportError("El paquete PBIP contiene una ruta insegura")
            total_size += info.file_size
            if total_size > 50 * 1024 * 1024:
                raise SemanticModelImportError("El paquete PBIP supera el limite de 50 MB")
            if info.filename.casefold().endswith(".tmdl"):
                try:
                    tmdl_parts.append(archive.read(info).decode("utf-8-sig"))
                except UnicodeDecodeError as exc:
                    raise SemanticModelImportError("Un archivo TMDL del paquete no es UTF-8 valido") from exc

    if not tmdl_parts:
        raise SemanticModelImportError("El paquete PBIP no contiene archivos .tmdl")
    return parse_tmdl_text("\n\n".join(tmdl_parts))


def _split_property(value: str) -> tuple[str, str]:
    if ":" not in value:
        return "", ""
    key, property_value = value.split(":", 1)
    return key.strip(), property_value.strip()


def _clean_name(value: str) -> str:
    value = value.rstrip(";").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _clean_value(value: str) -> str:
    return _clean_name(value.strip())


def _split_reference(value: str) -> tuple[str, str]:
    clean_value = _clean_value(value)
    bracket_match = re.match(r"^(.+?)\[([^]]+)\]$", clean_value)
    if bracket_match:
        return _clean_name(bracket_match.group(1).strip()), bracket_match.group(2).strip()
    if "." in clean_value:
        table_name, column_name = clean_value.rsplit(".", 1)
        return _clean_name(table_name.strip()), _clean_name(column_name.strip())
    return "", ""
