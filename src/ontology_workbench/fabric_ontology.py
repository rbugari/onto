"""Fabric IQ ontology, new TMDL-based experience, built from an approved release.

Format checked against Microsoft Learn (Ontology definition TMDL and Create ontology REST API, consulted 2026-11-24).
The package is ontology-first: entities, properties, relationships and rules without backing tables, because ONTO
does not know the workspace or Lakehouse; the bindings are added in Fabric. The old entity-type JSON experience
retires on 2027-01-31 and is no longer generated.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from ontology_workbench.export_enrichment import fabric_value_type, identifier, property_column, unique_name

FORMAT_VERSION = "fabric-ontology-tmdl-2026-11"
RETIREMENT_NOTICE = "La experiencia anterior de Ontology (JSON de entity types) se retira el 2027-01-31; este paquete usa la nueva (TMDL)."
_TMDL_TYPES = {"String": "string", "BigInt": "int64", "Double": "double", "DateTime": "dateTime", "Boolean": "boolean"}

# (element_type, name, status, target_artifact, action) consumed by the coverage report
CoverageRow = tuple[str, str, str, str, str]


def ontology_name(value: str) -> str:
    """Display name: starts with a letter, only letters, numbers and underscore (Create ontology API rule)."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^A-Za-z0-9_]+", "_", ascii_value).strip("_")
    if not clean or not clean[0].isalpha():
        clean = f"O_{clean}"
    return clean[:99]


def platform_file(display_name: str, seed: str) -> dict[str, object]:
    digest = hashlib.sha256(f"{seed}:Ontology:{display_name}".encode()).hexdigest()
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Ontology", "displayName": display_name},
        "config": {"version": "2.0", "logicalId": f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"},
    }


def build_ontology_parts(model) -> tuple[dict[str, str], list[CoverageRow]]:
    coverage: list[CoverageRow] = []
    entity_names: dict[str, str] = {}
    used: set[str] = set()
    for concept in model.concepts:
        entity_names[str(concept["id"])] = unique_name(identifier(str(concept["name"])), used)

    parts: dict[str, str] = {"database.tmdl": "database\n\tcompatibilityLevel: 1000000\n", "namespaces/default.tmdl": "namespace default\n\tlineageTag: default\n"}
    for concept in model.concepts:
        concept_id = str(concept["id"])
        parts[f"entities/{entity_names[concept_id]}.tmdl"] = _entity(model, concept, entity_names[concept_id], coverage)
        coverage.append(("concept", str(concept["name"]), "native", "Entity type de la ontologia", ""))

    relationships, used_relations = [], set()
    for relation in model.relationships:
        linked = [str(item) for item in relation.get("linked_candidate_ids", [])]
        if len(linked) == 2 and all(item in entity_names for item in linked):
            relationships.append(_entity_relationship(relation, entity_names[linked[0]], entity_names[linked[1]], used_relations))
            coverage.append(("relationship", str(relation["name"]), "native", "Entity relationship", "Sin tabla de respaldo: se vincula en Fabric."))
        else:
            coverage.append(("relationship", str(relation["name"]), "instructions", "Instrucciones del Data Agent",
                             "La relacion no une dos conceptos; se describe como instruccion."))
    if relationships:
        parts["entityRelationships.tmdl"] = "\n".join(relationships)

    rule_names: set[str] = set()
    for rule in model.rules:
        referenced = _referenced_entities(rule, model.concepts, entity_names)
        if referenced:
            name = unique_name(identifier(str(rule["name"])), rule_names)
            parts[f"rules/{name}.tmdl"] = _rule(rule, name, referenced)
            coverage.append(("business_rule", str(rule["name"]), "native", "Rule de la ontologia", ""))
        else:
            coverage.append(("business_rule", str(rule["name"]), "instructions", "Instrucciones del Data Agent",
                             "Ninguna entidad aprobada aparece en la regla; se deja como instruccion."))

    refs = [f"ref entity {name}" for name in sorted(entity_names.values())]
    refs += ["", "ref namespace default"] + (["", *[f"ref rule {name}" for name in sorted(rule_names)]] if rule_names else [])
    parts["model.tmdl"] = "model Model\n\n" + "\n".join(refs) + "\n"
    return parts, coverage


def _entity(model, concept: dict[str, object], name: str, coverage: list[CoverageRow]) -> str:
    concept_id = str(concept["id"])
    lines = [f"/// {_one_line(str(concept['definition']))}", f"entity {name}"]
    lines += [f"\tsynonym {synonym}" for synonym in model.synonyms_for(concept_id)]
    property_names: set[str] = set()
    properties = []
    for prop in model.properties:
        if concept_id not in prop.get("linked_candidate_ids", []):
            continue
        match = property_column(model, concept_id, prop, model.columns, model.tables_by_concept)
        value_type = fabric_value_type(match[2]) if match else None
        properties.append((unique_name(identifier(str(prop["name"])), property_names), prop, _TMDL_TYPES.get(value_type or "String", "string")))
        if value_type:
            coverage.append(("property", str(prop["name"]), "native", "Propiedad del entity type",
                             f"Tipo {value_type} tomado de {match[0]}.{match[1]}; vincularla a esa columna en Fabric."))
        else:
            coverage.append(("property", str(prop["name"]), "needs_completion", "Propiedad del entity type",
                             "Revisar el tipo de dato (se genera string; no hay columna aprobada que lo respalde) y vincularla a una columna."))
    if not properties:
        properties.append(("Nombre", {"definition": f"Nombre de {concept['name']} (propiedad por defecto de ONTO)"}, "string"))
    for prop_name, prop, data_type in properties:
        lines += ["", f"\t/// {_one_line(str(prop['definition']))}", f"\tproperty {prop_name}", f"\t\tdataType: {data_type}"]
    return "\n".join(lines) + "\n"


def _entity_relationship(relation: dict[str, object], source: str, target: str, used: set[str]) -> str:
    name = unique_name(str(relation["name"]).strip() or "Relacion", used)
    return "\n".join([
        f"/// {_one_line(str(relation['definition']))}",
        f"entityRelationship {_quote(name)}",
        f"\tfromEntity: {source}",
        f"\ttoEntity: {target}",
        "",
    ])


def _rule(rule: dict[str, object], name: str, entities: list[str]) -> str:
    lines = [f"rule {name}", f"\tstatement: {_one_line(str(rule['definition']))}"]
    for entity in entities:
        lines += ["", f"\truleReferencedEntity {entity}"]
    return "\n".join(lines) + "\n"


def _referenced_entities(rule: dict[str, object], concepts, entity_names: dict[str, str]) -> list[str]:
    text = f"{rule['name']} {rule['definition']}".casefold()
    return [entity_names[str(concept["id"])] for concept in concepts if str(concept["name"]).casefold() in text]


def _quote(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def _one_line(value: str) -> str:
    return " ".join(value.split())
