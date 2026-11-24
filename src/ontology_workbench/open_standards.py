"""Open-standard exports of an approved release: OWL/Turtle and an Apache Ossie semantic model.

- `ontology.ttl`: classes, datatype/object properties, labels, comments and synonyms. Fabric imports it into an empty
  ontology item; rules, KPIs and constraints have no OWL representation here and stay in the platform packages.
- `semantic_model.ossie.yaml`: EXPERIMENTAL. Apache Ossie is incubating; written against spec 0.3.0.dev0 (core-spec/spec.md,
  consulted 2026-11-24). Datasets come from the approved tables, relationships from key columns present in the release.
  KPIs are not emitted as metrics because the release carries no approved SQL expression. The document is JSON, which is
  valid YAML, so it can be validated without extra tooling.
"""
from __future__ import annotations

import json
import re

from ontology_workbench.export_enrichment import fabric_value_type, identifier, property_column, unique_name

OSSIE_SPEC_VERSION = "0.3.0.dev0"
_XSD = {"String": "string", "BigInt": "long", "Double": "double", "DateTime": "dateTime", "Boolean": "boolean"}
_OSSIE_BY_TOKEN = {
    "decimal": "Decimal", "numeric": "Decimal", "money": "Decimal", "smallmoney": "Decimal", "number": "Decimal",
    "date": "Date", "time": "Time", "datetimeoffset": "DateTimeTz",
}
_OSSIE_BY_VALUE_TYPE = {"String": "String", "BigInt": "Integer", "Double": "Float", "DateTime": "DateTime", "Boolean": "Boolean"}


def build_open_standard_files(model) -> dict[str, str]:
    files = {"open_standards/ontology.ttl": _turtle(model), "open_standards/README.md": _readme(model)}
    ossie = _ossie_model(model)
    if ossie:
        files["open_standards/semantic_model.ossie.yaml"] = json.dumps(ossie, ensure_ascii=False, indent=2) + "\n"
    return files


def _turtle(model) -> str:
    base = f"urn:onto:{identifier(model.project_id)}:{identifier(model.release_id)}#"
    names: dict[str, str] = {}
    used: set[str] = set()
    for concept in model.concepts:
        names[str(concept["id"])] = unique_name(identifier(str(concept["name"])), used)
    lines = [
        f"@prefix : <{base}> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .", "",
        f"<urn:onto:{identifier(model.project_id)}:{identifier(model.release_id)}> a owl:Ontology ;",
        f"    rdfs:label {_literal('Dominio ' + model.domain)} ;",
        f"    rdfs:comment {_literal('Release ONTO ' + model.release_id + ', aprobada por revision humana.')} .", "",
    ]
    for concept in model.concepts:
        concept_id = str(concept["id"])
        statements = ["a owl:Class", f"rdfs:label {_literal(str(concept['name']))}", f"rdfs:comment {_literal(str(concept['definition']))}"]
        statements += [f"skos:altLabel {_literal(synonym)}" for synonym in model.synonyms_for(concept_id)]
        lines += [f":{names[concept_id]} " + " ;\n    ".join(statements) + " .", ""]
    property_names: set[str] = set(names.values())
    for prop in model.properties:
        owner = next((str(item) for item in prop.get("linked_candidate_ids", []) if str(item) in names), "")
        if not owner:
            continue
        match = property_column(model, owner, str(prop["name"]), model.columns, model.tables_by_concept)
        xsd = _XSD.get(fabric_value_type(match[2]) or "String", "string") if match else "string"
        local = unique_name(f"{names[owner]}_{identifier(str(prop['name']))}", property_names)
        lines += [
            f":{local} a owl:DatatypeProperty ;\n    rdfs:label {_literal(str(prop['name']))} ;\n"
            f"    rdfs:comment {_literal(str(prop['definition']))} ;\n    rdfs:domain :{names[owner]} ;\n    rdfs:range xsd:{xsd} .", ""
        ]
    for relation in model.relationships:
        linked = [str(item) for item in relation.get("linked_candidate_ids", [])]
        if len(linked) != 2 or not all(item in names for item in linked):
            continue
        local = unique_name(identifier(str(relation["name"])), property_names)
        lines += [
            f":{local} a owl:ObjectProperty ;\n    rdfs:label {_literal(str(relation['name']))} ;\n"
            f"    rdfs:comment {_literal(str(relation['definition']))} ;\n    rdfs:domain :{names[linked[0]]} ;\n    rdfs:range :{names[linked[1]]} .", ""
        ]
    return "\n".join(lines)


def _ossie_model(model) -> dict[str, object] | None:
    tables = sorted({model.asset_table(asset) for asset in model.assets if model.asset_kind(asset) == "table"} | set(model.columns))
    if not tables:
        return None
    concept_by_table: dict[str, dict[str, object]] = {}
    for _binding, business, asset in model.binding_pairs():
        if business["id"] in model.concept_ids:
            concept_by_table.setdefault(model.asset_table(asset), business)
    dataset_names: dict[str, str] = {}
    used: set[str] = set()
    for table in tables:
        dataset_names[table] = unique_name(identifier(table.split(".")[-1]), used)
    key_columns = {join["right_table"]: join["right_column"] for join in model.joins}
    datasets = []
    for table in tables:
        dataset: dict[str, object] = {"name": dataset_names[table], "source": table}
        concept = concept_by_table.get(table)
        if concept:
            dataset["description"] = " ".join(str(concept["definition"]).split())
            synonyms = model.synonyms_for(str(concept["id"]))
            if synonyms:
                dataset["ai_context"] = {"synonyms": synonyms}
        fields = [_field(model, name, data_type, concept) for name, data_type in model.columns.get(table, {}).values()]
        if table in key_columns and any(field["name"] == key_columns[table] for field in fields):
            dataset["primary_key"] = [key_columns[table]]
        if fields:
            dataset["fields"] = fields
        datasets.append(dataset)
    relation_names: set[str] = set()
    relationships = [
        {
            "name": unique_name(identifier(join["relationship"]), relation_names),
            "from": dataset_names[join["left_table"]], "to": dataset_names[join["right_table"]],
            "from_columns": [join["left_column"]], "to_columns": [join["right_column"]],
        }
        for join in model.joins
        if join["left_table"] in dataset_names and join["right_table"] in dataset_names
    ]
    instructions = f"Modelo preparado por ONTO desde la release {model.release_id} (experimental). Usar solo el conocimiento aprobado."
    document: dict[str, object] = {
        "version": OSSIE_SPEC_VERSION,
        "name": identifier(f"{model.domain}_{model.release_id}"),
        "description": f"Dominio {model.domain}, release {model.release_id}.",
        "ai_context": {"instructions": instructions},
        "datasets": datasets,
    }
    if relationships:
        document["relationships"] = relationships
    return document


def _field(model, column: str, data_type: str, concept) -> dict[str, object]:
    field: dict[str, object] = {"name": column, "expression": {"sql": column}}
    ossie_type = _ossie_type(data_type)
    if ossie_type:
        field["datatype"] = ossie_type
    if concept:
        wanted = re.sub(r"[^a-z0-9]", "", column.casefold())
        prop = next((item for item in model.properties if str(concept["id"]) in item.get("linked_candidate_ids", [])
                     and re.sub(r"[^a-z0-9]", "", str(item["name"]).casefold()) == wanted), None)
        if prop:
            field["description"] = " ".join(str(prop["definition"]).split())
    return field


def _ossie_type(data_type: str) -> str:
    base = re.split(r"[(\s<]", data_type.strip().lower())[0]
    if base in _OSSIE_BY_TOKEN:
        return _OSSIE_BY_TOKEN[base]
    value_type = fabric_value_type(data_type)
    return _OSSIE_BY_VALUE_TYPE.get(value_type or "", "")


def _literal(value: str) -> str:
    text = " ".join(value.split()).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _readme(model) -> str:
    return "\n".join([
        f"# Estandares abiertos de la release {model.release_id}", "",
        "- `ontology.ttl`: OWL en Turtle (clases, propiedades de datos y de objetos, etiquetas, comentarios y sinonimos `skos:altLabel`). "
        "Fabric lo importa en una ontologia **vacia** (Importar ontologia). Reglas, KPIs y restricciones no tienen representacion aqui: "
        "van en los paquetes de plataforma.",
        f"- `semantic_model.ossie.yaml` (experimental): modelo semantico Apache Ossie {OSSIE_SPEC_VERSION} (incubating, la especificacion puede cambiar). "
        "Contiene datasets, campos y relaciones aprobados; no incluye metricas porque la release no guarda una expresion SQL aprobada. "
        "Esta escrito en JSON, que es YAML valido.", "",
    ])
