"""Importable packages that hand an approved release to the client's platform (Fabric IQ or Databricks).

ONTO does not publish: it writes files in the formats each platform imports, plus a coverage report
that says what the platform can implement natively and what stays in ONTO (plan B).
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import unicodedata

from ontology_workbench.export_enrichment import (
    column_index, concept_tables, fabric_value_type, item_owner, kpi_formula, page_sections,
    placeholder_counts, property_column, relationship_joins,
)
from ontology_workbench.platform_reach import (  # noqa: F401  (re-exported for callers of this module)
    BRIDGE_HINTS, PLATFORM_REACH, TARGET_LABELS, recommend_route, reachable,
)

COVERAGE_LABELS = {
    "native": "Se implementa en la plataforma",
    "needs_completion": "Se implementa en la plataforma, falta completar un dato",
    "instructions": "Se implementa como instruccion o documento del agente",
    "outside_platform": "Fuera del alcance de la plataforma (puente o plan B)",
}
INSTRUCTION_CHAR_LIMIT = 19_000


def build_platform_export(
    release: dict[str, object], target: str, settings: dict[str, str] | None = None
) -> dict[str, object]:
    settings = {key: str(value).strip() for key, value in (settings or {}).items() if str(value).strip()}
    model = _ReleaseModel(release)
    if target == "fabric":
        files, coverage = _fabric_files(model, settings)
    elif target == "databricks":
        files, coverage = _databricks_files(model, settings)
    else:
        raise ValueError("Destino de interoperabilidad no soportado")
    summary = _coverage_summary(coverage, model, target)
    summary["pending_completion"] = _count_by_type(coverage, "needs_completion")
    summary["placeholders"] = placeholder_counts(files)
    files["coverage_report.md"] = _coverage_markdown(model, target, coverage, summary)
    return {"files": files, "coverage": coverage, "summary": summary}


def _count_by_type(coverage: list[dict[str, str]], status: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in coverage:
        if item["status"] == status:
            counts[item["element_type"]] = counts.get(item["element_type"], 0) + 1
    return counts


class _ReleaseModel:
    def __init__(self, release: dict[str, object]) -> None:
        manifest = dict(release["manifest"])
        ontology = dict(release["canonical_ontology"])
        context_pack = dict(release.get("agent_context_pack", {}))
        self.release_id = str(manifest["release_id"])
        self.project_id = str(manifest["project_id"])
        scope = dict(dict(manifest.get("source_assessment", {})).get("scope", {}))
        self.domain = str(scope.get("domain_id") or self.project_id)
        self.concepts = [dict(item) for item in ontology.get("concepts", [])]
        self.kpis = [dict(item) for item in ontology.get("kpis", [])]
        self.rules = [dict(item) for item in ontology.get("business_rules", [])]
        self.assets = [dict(item) for item in ontology.get("technical_assets", [])]
        self.properties = [dict(item) for item in ontology.get("properties", [])]
        self.relationships = [dict(item) for item in ontology.get("relationships", [])]
        self.synonyms = [dict(item) for item in ontology.get("synonyms", [])]
        self.constraints = [dict(item) for item in ontology.get("constraints", [])]
        self.bindings = [dict(item) for item in ontology.get("data_bindings", [])]
        self.query_catalog = dict(context_pack.get("query_catalog", {}))
        self.by_id = {str(item["id"]): item for item in [*self.concepts, *self.kpis, *self.rules, *self.assets]}
        self.concept_ids = {str(item["id"]) for item in self.concepts}
        self.asset_ids = {str(item["id"]) for item in self.assets}
        self.columns = column_index(self)
        self.tables_by_concept = concept_tables(self)
        self.joins = relationship_joins(self, self.columns, self.tables_by_concept)
        self.example_questions = [
            str(spec["example_question"]) for spec in self.query_catalog.values() if spec.get("example_question")
        ]

    def synonyms_for(self, item_id: str) -> list[str]:
        return [str(item["name"]) for item in self.synonyms if item_id in item.get("linked_candidate_ids", [])]

    def asset_platform(self, asset: dict[str, object]) -> str:
        metadata = dict(asset.get("technical_metadata", {}))
        if metadata.get("source.platform"):
            return str(metadata["source.platform"])
        return "fabric" if metadata.get("fabric.objectType") else "other"

    def asset_table(self, asset: dict[str, object]) -> str:
        metadata = dict(asset.get("technical_metadata", {}))
        if metadata.get("fabric.table"):
            return f"{metadata.get('fabric.schema', 'dbo')}.{metadata['fabric.table']}"
        return str(metadata.get("bim.table") or asset["name"])

    def asset_kind(self, asset: dict[str, object]) -> str:
        metadata = dict(asset.get("technical_metadata", {}))
        return str(metadata.get("fabric.objectType") or metadata.get("bim.objectType") or "table")

    def binding_pairs(self) -> list[tuple[dict[str, object], dict[str, object], dict[str, object]]]:
        pairs = []
        for binding in self.bindings:
            linked = [str(item) for item in binding.get("linked_candidate_ids", [])]
            business = next((self.by_id[item] for item in linked if item in self.by_id and item not in self.asset_ids), None)
            asset = next((self.by_id[item] for item in linked if item in self.asset_ids), None)
            if business and asset:
                pairs.append((binding, business, asset))
        return pairs


# ---------------------------------------------------------------- Fabric

def _fabric_files(model: _ReleaseModel, settings: dict[str, str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    coverage: list[dict[str, str]] = []
    ontology_name = _fabric_name(settings.get("ontology_name") or f"{model.domain}_ontology")
    entity_ids: dict[str, str] = {}
    parts: dict[str, dict[str, object]] = {"definition.json": {}}
    for concept in model.concepts:
        entity_id = _bigint(model.release_id, concept["id"])
        entity_ids[str(concept["id"])] = entity_id
        name_property = {"id": _bigint(entity_id, "name"), "name": "Nombre", "redefines": None,
                         "baseTypeNamespaceType": None, "valueType": "String"}
        properties = [name_property]
        for prop in model.properties:
            if concept["id"] in prop.get("linked_candidate_ids", []):
                match = property_column(model, str(concept["id"]), str(prop["name"]), model.columns, model.tables_by_concept)
                value_type = fabric_value_type(match[2]) if match else None
                properties.append({"id": _bigint(entity_id, prop["id"]), "name": _fabric_name(str(prop["name"])),
                                   "redefines": None, "baseTypeNamespaceType": None, "valueType": value_type or "String"})
                if value_type:
                    coverage.append(_cov("property", prop["name"], "native", "Propiedad de EntityType",
                                         f"Tipo {value_type} tomado de {match[0]}.{match[1]}; vincularla a esa columna en el DataBinding."))
                else:
                    coverage.append(_cov("property", prop["name"], "needs_completion", "Propiedad de EntityType",
                                         "Revisar el tipo de dato (se genera String; no hay columna aprobada que lo respalde) y vincularla a una columna."))
        parts[f"EntityTypes/{entity_id}/definition.json"] = {
            "id": entity_id, "namespace": "usertypes", "baseEntityTypeId": None,
            "name": _fabric_name(str(concept["name"])), "entityIdParts": [name_property["id"]],
            "displayNamePropertyId": name_property["id"], "namespaceType": "Custom",
            "visibility": "Visible", "properties": properties,
        }
        coverage.append(_cov("concept", concept["name"], "native", "EntityType de la ontologia", ""))
    for relation in model.relationships:
        linked = [str(item) for item in relation.get("linked_candidate_ids", [])]
        if len(linked) == 2 and all(item in entity_ids for item in linked):
            relation_id = _bigint(model.release_id, relation["id"])
            parts[f"RelationshipTypes/{relation_id}/definition.json"] = {
                "namespace": "usertypes", "id": relation_id, "name": _fabric_name(str(relation["name"])),
                "namespaceType": "Custom", "source": {"entityTypeId": entity_ids[linked[0]]},
                "target": {"entityTypeId": entity_ids[linked[1]]},
            }
            coverage.append(_cov("relationship", relation["name"], "native", "RelationshipType", ""))
        else:
            coverage.append(_cov("relationship", relation["name"], "instructions", "Instrucciones del Data Agent",
                                 "La relacion no une dos conceptos; se describe como instruccion."))
    for binding, business, asset in model.binding_pairs():
        platform = model.asset_platform(asset)
        if reachable(platform, "fabric"):
            coverage.append(_cov("data_binding", binding["name"], "needs_completion", "DataBinding a tabla de Lakehouse",
                                 f"Vincular '{business['name']}' con {model.asset_table(asset)} desde Fabric (requiere tabla en Lakehouse)."))
        else:
            coverage.append(_cov("data_binding", binding["name"], "outside_platform", "Plan B en ONTO", BRIDGE_HINTS["fabric"]))
    _asset_coverage(model, "fabric", coverage)
    for kpi in model.kpis:
        formula = kpi_formula(model, str(kpi["id"]))
        coverage.append(_cov("kpi", kpi["name"], "instructions", "Instrucciones del Data Agent",
                             "La formula DAX del modelo semantico va en las instrucciones; validarla antes de usarla." if formula
                             else "Para calcularlo, agregar una medida en el modelo semantico o un ejemplo SQL al Data Agent."))
    for rule in model.rules:
        coverage.append(_cov("business_rule", rule["name"], "instructions", "Instrucciones del Data Agent", ""))
    for item in model.synonyms:
        coverage.append(_cov("synonym", item["name"], "instructions", "Instrucciones del Data Agent", ""))
    for item in model.constraints:
        coverage.append(_cov("constraint", item["name"], "instructions", "Instrucciones del Data Agent", ""))

    item_dir = f"fabric/ontology/{ontology_name}.Ontology"
    platform_file = _platform_file("Ontology", ontology_name, model.release_id)
    files = {f"{item_dir}/.platform": _json(platform_file)}
    files.update({f"{item_dir}/{path}": _json(payload) for path, payload in parts.items()})
    files["fabric/ontology/create_ontology_request.json"] = _json(
        {
            "displayName": ontology_name,
            "description": f"Ontologia preparada por ONTO desde la release {model.release_id}.",
            "definition": {
                "parts": [
                    {"path": path, "payload": _b64(_json(payload)), "payloadType": "InlineBase64"}
                    for path, payload in {".platform": {"metadata": {"type": "Ontology", "displayName": ontology_name}}, **parts}.items()
                ]
            },
        }
    )
    agent_dir = f"fabric/data_agent/{ontology_name}_agent.DataAgent/Files/Config"
    files[f"{agent_dir}/data_agent.json"] = _json(
        {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/dataAgent/2.1.0/schema.json"}
    )
    files[f"{agent_dir}/draft/stage_config.json"] = _json(
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/stageConfiguration/1.0.0/schema.json",
            "aiInstructions": _instructions(model, "fabric"),
        }
    )
    files["fabric/README_IMPLEMENTACION.md"] = _fabric_readme(model, ontology_name)
    return files, coverage


def _fabric_readme(model: _ReleaseModel, ontology_name: str) -> str:
    return "\n".join([
        f"# Implementar la release {model.release_id} en Microsoft Fabric", "",
        "Este paquete lo genero ONTO. No publica nada: el equipo de Fabric lo importa y lo completa.", "",
        "## 1. Ontologia (Fabric IQ)", "",
        f"- Carpeta `ontology/{ontology_name}.Ontology/`: formato de integracion Git. Copiarla al repositorio conectado al workspace y sincronizar.",
        "- Alternativa por API: `POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/ontologies` con el cuerpo de `ontology/create_ontology_request.json`.",
        "- Contiene tipos de entidad (conceptos aprobados), propiedades y relaciones. Cada entidad trae la propiedad `Nombre` como identificador por defecto.",
        "- Los enlaces a datos (DataBindings) se completan en Fabric: requieren una tabla de Lakehouse y el mapeo columna-propiedad. Ver `coverage_report.md`.", "",
        "## 2. Data Agent", "",
        f"- Carpeta `data_agent/{ontology_name}_agent.DataAgent/`: `aiInstructions` con conceptos, KPIs, reglas, sinonimos y la regla de abstencion.",
        "- Agregar como fuente de datos el Lakehouse, Warehouse o modelo semantico que corresponda y publicar el agente.", "",
        "## 3. Lo que queda afuera", "",
        "- Revisar `coverage_report.md`: lo marcado como fuera de alcance necesita Mirroring/shortcut o queda en ONTO (plan B).", "",
    ])


# ---------------------------------------------------------------- Databricks

def _databricks_files(model: _ReleaseModel, settings: dict[str, str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    coverage: list[dict[str, str]] = []
    catalog = settings.get("catalog", "main")
    files: dict[str, str] = {}
    bindings_by_business: dict[str, list[dict[str, object]]] = {}
    sql_lines = [
        f"-- Comentarios y tags de Unity Catalog preparados por ONTO (release {model.release_id}).",
        "-- Revisar identificadores antes de ejecutar. Requiere permiso MODIFY/APPLY TAG sobre cada objeto.", "",
    ]
    tables: dict[str, str] = {}
    databricks_joins = [
        join for join in model.joins
        if reachable(_table_platform(model, join["left_table"]), "databricks")
        and reachable(_table_platform(model, join["right_table"]), "databricks")
    ]
    for binding, business, asset in model.binding_pairs():
        bindings_by_business.setdefault(str(business["id"]), []).append(asset)
    for binding, business, asset in model.binding_pairs():
        bindings_by_business.setdefault(str(business["id"]), []).append(asset)
        if not reachable(model.asset_platform(asset), "databricks"):
            coverage.append(_cov("data_binding", binding["name"], "outside_platform", "Plan B en ONTO", BRIDGE_HINTS["databricks"]))
            continue
        table = _three_part(model.asset_table(asset), catalog)
        comment = _sql_text(f"{business['name']}: {business['definition']}")
        if model.asset_kind(asset) == "column":
            column = str(asset["name"]).split("[")[-1].rstrip("]").split(".")[-1]
            sql_lines.append(f"ALTER TABLE {table} ALTER COLUMN `{column}` COMMENT '{comment}';")
        else:
            sql_lines.append(f"COMMENT ON TABLE {table} IS '{comment}';")
            tables[table] = str(business["definition"])
        sql_lines.append(f"ALTER TABLE {table} SET TAGS ('onto_domain' = '{_sql_text(model.domain)}', 'onto_release' = '{model.release_id}');")
        coverage.append(_cov("data_binding", binding["name"], "native", "Comentario y tags en Unity Catalog", ""))
    _asset_coverage(model, "databricks", coverage)

    for item in [*model.concepts, *model.kpis]:
        files[f"databricks/pages/{_slug(str(item['name']))}.md"] = _page_markdown(model, item, bindings_by_business, catalog)
        coverage.append(_cov("concept" if item in model.concepts else "kpi", item["name"], "native",
                             "Page (Unity Catalog semantics)", "Importar con 'Bulk import pages' desde la carpeta pages/."))
    for kpi in model.kpis:
        assets = bindings_by_business.get(str(kpi["id"]), [])
        source_table = model.asset_table(assets[0]) if assets else ""
        source = _three_part(source_table, catalog) if assets else "COMPLETAR.catalogo.tabla"
        joins = [join for join in databricks_joins if join["left_table"] == source_table]
        files[f"databricks/metric_views/{_slug(str(kpi['name']))}.yaml"] = _metric_view_yaml(model, kpi, source, joins, catalog)
        coverage.append(_cov("kpi", kpi["name"], "needs_completion", "Metric view (YAML 1.1)",
                             "Completar la expresion SQL agregada de la medida y la tabla fuente."))
    for relation in model.relationships:
        has_join = any(join["relationship"] == relation["name"] for join in databricks_joins)
        coverage.append(_cov("relationship", relation["name"], "native" if has_join else "instructions",
                             "Join del Genie Agent (join_specs)" if has_join else "Page y instrucciones de Genie",
                             "" if has_join else "Si ambos conceptos tienen tabla y su clave, declarar el join en el Genie Agent (join_specs)."))
    for prop in model.properties:
        owner_concept = next((str(item) for item in prop.get("linked_candidate_ids", []) if str(item) in model.concept_ids), "")
        match = property_column(model, owner_concept, str(prop["name"]), model.columns, model.tables_by_concept)
        if match and reachable(_table_platform(model, match[0]), "databricks"):
            table = _three_part(match[0], catalog)
            sql_lines.append(
                f"ALTER TABLE {table} ALTER COLUMN `{match[1]}` COMMENT '{_sql_text(str(prop['name']) + ': ' + str(prop['definition']))}';"
            )
            coverage.append(_cov("property", prop["name"], "native", "Comentario de columna en Unity Catalog", ""))
        else:
            coverage.append(_cov("property", prop["name"], "instructions", "Page del concepto", ""))
    files["databricks/unity_catalog_comments.sql"] = "\n".join(sql_lines) + "\n"
    for rule in model.rules:
        coverage.append(_cov("business_rule", rule["name"], "instructions", "Instrucciones del Genie Agent", ""))
    for item in model.synonyms:
        coverage.append(_cov("synonym", item["name"], "native", "Sinonimos de la Page", ""))
    for item in model.constraints:
        coverage.append(_cov("constraint", item["name"], "instructions", "Instrucciones del Genie Agent", ""))

    instructions = _instructions(model, "databricks")
    files["databricks/genie_workspace_instructions.md"] = instructions
    files["databricks/genie_agent_create_request.json"] = _json(
        _genie_request(model, settings, tables, instructions, databricks_joins, catalog)
    )
    files["databricks/README_IMPLEMENTACION.md"] = _databricks_readme(model)
    return files, coverage


def _table_platform(model: _ReleaseModel, table: str) -> str:
    return next((model.asset_platform(asset) for asset in model.assets if model.asset_table(asset) == table), "other")



def _page_markdown(model: _ReleaseModel, item: dict[str, object], bindings: dict[str, list[dict[str, object]]], catalog: str) -> str:
    item_id = str(item["id"])
    related = [
        str(rel["name"]) for rel in model.relationships if item_id in rel.get("linked_candidate_ids", [])
    ]
    properties = []
    for prop in model.properties:
        if item_id in prop.get("linked_candidate_ids", []):
            match = property_column(model, item_id, str(prop["name"]), model.columns, model.tables_by_concept)
            value_type = fabric_value_type(match[2]) if match else None
            properties.append(f"{prop['name']} ({match[1]}, {value_type})" if value_type else str(prop["name"]))
    assets = [_three_part(model.asset_table(asset), catalog) for asset in bindings.get(item_id, [])]
    evidence = dict(item.get("source_binding", {}))
    sections = page_sections(model, item, model.example_questions)
    owner = item_owner(model, item_id)
    lines = [
        f"# {item['name']}", "",
        f"**Dominio:** {model.domain}  ",
        f"**Responsable:** {owner or 'COMPLETAR_RESPONSABLE'}  ",
        f"**Descripcion:** {_one_line(str(item['definition']))}  ",
        f"**Sinonimos:** {', '.join(model.synonyms_for(item_id)) or '-'}", "",
        "## Definicion", "", str(item["definition"]), "",
    ]
    if sections["usage"]:
        lines += ["## Uso de negocio", "", *[f"- {text}" for text in sections["usage"]], ""]
    if sections["examples"]:
        lines += ["## Ejemplos", "", *[f"- {question}" for question in sections["examples"]], ""]
    if properties:
        lines += ["## Propiedades", "", *[f"- {name}" for name in properties], ""]
    if related:
        lines += ["## Relaciones", "", *[f"- {name}" for name in related], ""]
    if assets:
        lines += ["## Activos relacionados", "", *[f"- `{name}`" for name in assets], ""]
    lines += [
        "## Fuentes", "",
        f"- Release ONTO `{model.release_id}` (aprobada por revision humana).",
        f"- Evidencia: {evidence.get('source_document_id', '-')} / {evidence.get('source_chunk_id', '-')}", "",
    ]
    return "\n".join(lines)


def _metric_view_yaml(
    model: _ReleaseModel, kpi: dict[str, object], source: str, joins: list[dict[str, str]], catalog: str
) -> str:
    synonyms = model.synonyms_for(str(kpi["id"]))[:10]
    formula = kpi_formula(model, str(kpi["id"]))
    lines = []
    if formula:
        lines.append(f"# Propuesta (DAX del modelo semantico; convertir a SQL agregado y validar): {formula}")
    lines += [
        "version: 1.1",
        f"source: {source}",
        f"comment: {json.dumps(_one_line(str(kpi['definition'])), ensure_ascii=False)}",
    ]
    if joins:
        lines.append("joins:")
        for join in joins:
            alias = _slug(join["right_table"].split(".")[-1]).replace("-", "_")
            lines += [
                f"  - name: {alias}",
                f"    source: {_three_part(join['right_table'], catalog)}",
                f"    \"on\": source.{join['left_column']} = {alias}.{join['right_column']}",
            ]
    lines += [
        "measures:",
        f"  - name: {_slug(str(kpi['name'])).replace('-', '_')}",
        '    expr: "COMPLETAR_EXPRESION_AGREGADA"',
        f"    display_name: {json.dumps(str(kpi['name'])[:255], ensure_ascii=False)}",
        f"    comment: {json.dumps(_one_line(str(kpi['definition'])), ensure_ascii=False)}",
    ]
    if synonyms:
        lines.append(f"    synonyms: {json.dumps(synonyms, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def _genie_request(
    model: _ReleaseModel, settings: dict[str, str], tables: dict[str, str], instructions: str,
    joins: list[dict[str, str]], catalog: str,
) -> dict[str, object]:
    questions = list(model.example_questions) or [f"Que es {concept['name']}?" for concept in model.concepts[:5]]
    table_sources = {identifier: [_one_line(description)[:1000]] for identifier, description in tables.items()}
    join_specs = []
    for join in joins:
        left, right = _three_part(join["left_table"], catalog), _three_part(join["right_table"], catalog)
        left_alias, right_alias = (_slug(name.split(".")[-1]).replace("-", "_") for name in (join["left_table"], join["right_table"]))
        table_sources.setdefault(left, [])
        table_sources.setdefault(right, [])
        join_specs.append({
            "id": _hex_id(model.release_id, "join", left, right, join["left_column"]),
            "left": {"identifier": left, "alias": left_alias},
            "right": {"identifier": right, "alias": right_alias},
            "sql": [
                f"`{left_alias}`.`{join['left_column']}` = `{right_alias}`.`{join['right_column']}`",
                "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--",
            ],
        })
    instruction_block: dict[str, object] = {
        "text_instructions": [{"id": _hex_id(model.release_id, "instructions"), "content": [instructions]}],
    }
    if join_specs:
        instruction_block["join_specs"] = sorted(join_specs, key=lambda item: item["id"])
    space = {
        "version": 2,
        "config": {
            "sample_questions": sorted(
                ({"id": _hex_id(model.release_id, "q", question), "question": [question]} for question in questions[:10]),
                key=lambda item: item["id"],
            )
        },
        "data_sources": {
            "tables": [
                {"identifier": identifier, **({"description": description} if description else {})}
                for identifier, description in sorted(table_sources.items())
            ]
        },
        "instructions": instruction_block,
    }
    return {
        "title": f"{model.domain} (ONTO)",
        "description": f"Agente preparado por ONTO desde la release {model.release_id}.",
        "warehouse_id": settings.get("warehouse_id", "COMPLETAR_WAREHOUSE_ID"),
        "parent_path": settings.get("parent_path", "/Workspace/Shared/onto"),
        "serialized_space": json.dumps(space, ensure_ascii=False),
    }


def _databricks_readme(model: _ReleaseModel) -> str:
    return "\n".join([
        f"# Implementar la release {model.release_id} en Databricks", "",
        "Este paquete lo genero ONTO. No publica nada: el equipo de Databricks lo importa y lo completa.",
        "Todo se integra a la Genie Ontology (capa de Unity Catalog semantics).", "",
        "## 1. Pages (conceptos y KPIs)", "",
        "- Carpeta `pages/`: un Markdown por concepto aprobado. En Discover > Pages usar **Bulk import pages** con Genie Code y adjuntar estos archivos.",
        f"- Crear antes el dominio `{model.domain}` (governed tag) para asociar las Pages.", "",
        "## 2. Comentarios y tags en Unity Catalog", "",
        "- `unity_catalog_comments.sql`: comentarios de tablas/columnas vinculadas y tags `onto_domain`/`onto_release`. Revisar identificadores y ejecutar en un SQL warehouse.", "",
        "## 3. Metric views (KPIs)", "",
        "- Carpeta `metric_views/`: un YAML por KPI. Completar `expr` y `source`, y crear con:",
        "  `CREATE VIEW catalogo.esquema.nombre WITH METRICS LANGUAGE YAML AS $$ <contenido> $$`", "",
        "## 4. Genie", "",
        "- `genie_agent_create_request.json`: cuerpo para `POST /api/2.0/genie/spaces` (completar `warehouse_id`).",
        "- `genie_workspace_instructions.md`: se puede copiar a `/Workspace/.genie_workspace_instructions.md` para Genie One.", "",
        "## 5. Lo que queda afuera", "",
        "- Revisar `coverage_report.md`: lo marcado como fuera de alcance necesita Lakehouse Federation/ingesta o queda en ONTO (plan B).", "",
    ])


# ---------------------------------------------------------------- Shared

def _asset_coverage(model: _ReleaseModel, target: str, coverage: list[dict[str, str]]) -> None:
    for asset in model.assets:
        if model.asset_kind(asset) != "table":
            continue
        platform = model.asset_platform(asset)
        if reachable(platform, target):
            coverage.append(_cov("technical_asset", asset["name"], "native", "Tabla disponible en la plataforma", ""))
        else:
            coverage.append(_cov("technical_asset", asset["name"], "outside_platform", f"Sistema de origen: {platform}", BRIDGE_HINTS[target]))


def _instructions(model: _ReleaseModel, target: str) -> str:
    def block(title: str, items: list[dict[str, object]]) -> list[str]:
        if not items:
            return []
        rows = []
        for item in items:
            synonyms = model.synonyms_for(str(item["id"]))
            suffix = f" (sinonimos: {', '.join(synonyms)})" if synonyms else ""
            formula = kpi_formula(model, str(item["id"])) if target == "fabric" and item in model.kpis else ""
            formula_text = f" Formula propuesta (DAX del modelo semantico, a validar): `{formula}`." if formula else ""
            rows.append(f"- **{item['name']}**{suffix}: {_one_line(str(item['definition']))}{formula_text}")
        return [f"## {title}", "", *rows, ""]

    lines = [
        f"# Conocimiento aprobado del dominio {model.domain}", "",
        f"Fuente: release ONTO `{model.release_id}`, aprobada por revision humana.",
        "Usa solo estas definiciones y reglas. Si una pregunta no se puede responder con ellas o con los datos autorizados, "
        "decilo explicitamente en lugar de suponer.", "",
        *block("Conceptos", model.concepts),
        *block("KPIs", model.kpis),
        *block("Reglas de negocio", model.rules),
        *block("Relaciones", model.relationships),
        *block("Restricciones", model.constraints),
    ]
    text = "\n".join(lines)
    if len(text) > INSTRUCTION_CHAR_LIMIT:
        text = text[:INSTRUCTION_CHAR_LIMIT] + "\n\n[Recortado: ver las Pages o la release completa.]"
    return text


def _coverage_summary(coverage: list[dict[str, str]], model: _ReleaseModel, target: str) -> dict[str, object]:
    counts = {status: sum(item["status"] == status for item in coverage) for status in COVERAGE_LABELS}
    outside = counts["outside_platform"]
    implementable = len(coverage) - outside
    tables = [item for item in coverage if item["element_type"] == "technical_asset"]
    route, reason = recommend_route(
        target, len(coverage), outside, len(tables), sum(item["status"] == "outside_platform" for item in tables)
    )
    return {
        "target": target,
        "target_label": TARGET_LABELS[target],
        "counts": counts,
        "total": len(coverage),
        "implementable_in_platform": implementable,
        "recommended_route": route,
        "route_reason": reason,
    }


def _coverage_markdown(model: _ReleaseModel, target: str, coverage: list[dict[str, str]], summary: dict[str, object]) -> str:
    lines = [
        f"# Cobertura en {TARGET_LABELS[target]}", "",
        f"- Release: `{model.release_id}`",
        f"- Elementos: {summary['total']}; implementables en la plataforma: {summary['implementable_in_platform']}.",
        f"- Ruta recomendada: **{summary['recommended_route']}**. {summary['route_reason']}", "",
        *_pending_lines(summary),
        "| Elemento | Nombre | Resultado | Donde queda | Accion |", "| --- | --- | --- | --- | --- |",
    ]
    for item in coverage:
        lines.append(
            f"| {item['element_type']} | {item['name']} | {COVERAGE_LABELS[item['status']]} | {item['target_artifact']} | {item['action'] or '-'} |"
        )
    return "\n".join(lines) + "\n"


def _pending_lines(summary: dict[str, object]) -> list[str]:
    pending, placeholders = dict(summary["pending_completion"]), dict(summary["placeholders"])
    if not pending and not placeholders:
        return ["Pendientes de completar en la plataforma: ninguno.", ""]
    lines = ["## Pendientes de completar", ""]
    if pending:
        lines.append("- Elementos a completar: " + ", ".join(f"{kind} {count}" for kind, count in sorted(pending.items())) + ".")
    if placeholders:
        lines.append("- Marcas `COMPLETAR` en archivos: " + ", ".join(f"`{path}` ({count})" for path, count in placeholders.items()) + ".")
    return [*lines, ""]


def _cov(element_type: str, name: object, status: str, target_artifact: str, action: str) -> dict[str, str]:
    return {"element_type": element_type, "name": str(name), "status": status, "target_artifact": target_artifact, "action": action}


def _platform_file(item_type: str, display_name: str, seed: str) -> dict[str, object]:
    digest = hashlib.sha256(f"{seed}:{item_type}:{display_name}".encode()).hexdigest()
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": item_type, "displayName": display_name},
        "config": {"version": "2.0", "logicalId": f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"},
    }


def _fabric_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_value).strip("_-")
    if not clean or not clean[0].isalpha():
        clean = f"E_{clean}"
    return clean[:128]


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")[:80] or "item"


def _bigint(*seeds: object) -> str:
    return str(int(hashlib.sha256(":".join(map(str, seeds)).encode()).hexdigest()[:15], 16) or 1)


def _hex_id(*seeds: object) -> str:
    return hashlib.sha256(":".join(map(str, seeds)).encode()).hexdigest()[:32]


def _three_part(name: str, catalog: str) -> str:
    parts = [part for part in name.split(".") if part]
    if len(parts) == 1:
        parts = [catalog, "default", *parts]
    elif len(parts) == 2:
        parts = [catalog, *parts]
    return ".".join(
        part if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) else f"`{part.replace('`', '``')}`"
        for part in parts[-3:]
    )


def _sql_text(value: str) -> str:
    return _one_line(value).replace("\\", "\\\\").replace("'", "\\'")[:1000]


def _one_line(value: str) -> str:
    return " ".join(value.split())


def _json(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")
