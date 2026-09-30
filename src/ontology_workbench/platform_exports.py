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

# Source platforms each target can reach without extra integration work.
PLATFORM_REACH = {
    "fabric": {"fabric", "powerbi"},
    "databricks": {"databricks"},
}
BRIDGE_HINTS = {
    "fabric": (
        "Traer la fuente a OneLake: Mirroring (si el origen es compatible), shortcut, o Copy job/pipeline de Data Factory "
        "(bases on-premises como MySQL/MariaDB via on-premises data gateway). Si no es viable, esa parte queda en ONTO (plan B)."
    ),
    "databricks": (
        "Registrar la fuente con Lakehouse Federation (MySQL, PostgreSQL, SQL Server, entre otras; requiere conectividad de red) "
        "o ingerirla a Delta. Si no es viable, esa parte queda en ONTO (plan B)."
    ),
}
TARGET_LABELS = {"fabric": "Microsoft Fabric (Fabric IQ)", "databricks": "Databricks (Unity Catalog / Genie)"}
COVERAGE_LABELS = {
    "native": "Se implementa en la plataforma",
    "needs_completion": "Se implementa en la plataforma, falta completar un dato",
    "instructions": "Se implementa como instruccion o documento del agente",
    "outside_platform": "Fuera del alcance de la plataforma (puente o plan B)",
}
INSTRUCTION_CHAR_LIMIT = 19_000


def reachable(source_platform: str, target: str) -> bool:
    return source_platform in PLATFORM_REACH.get(target, set())


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
    files["coverage_report.md"] = _coverage_markdown(model, target, coverage, summary)
    return {"files": files, "coverage": coverage, "summary": summary}


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
                properties.append({"id": _bigint(entity_id, prop["id"]), "name": _fabric_name(str(prop["name"])),
                                   "redefines": None, "baseTypeNamespaceType": None, "valueType": "String"})
                coverage.append(_cov("property", prop["name"], "needs_completion", "Propiedad de EntityType",
                                     "Revisar el tipo de dato (se genera String) y vincularla a una columna."))
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
        coverage.append(_cov("kpi", kpi["name"], "instructions", "Instrucciones del Data Agent",
                             "Para calcularlo, agregar una medida en el modelo semantico o un ejemplo SQL al Data Agent."))
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
            "aiInstructions": _instructions(model),
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
    files["databricks/unity_catalog_comments.sql"] = "\n".join(sql_lines) + "\n"

    for item in [*model.concepts, *model.kpis]:
        files[f"databricks/pages/{_slug(str(item['name']))}.md"] = _page_markdown(model, item, bindings_by_business, catalog)
        coverage.append(_cov("concept" if item in model.concepts else "kpi", item["name"], "native",
                             "Page (Unity Catalog semantics)", "Importar con 'Bulk import pages' desde la carpeta pages/."))
    for kpi in model.kpis:
        assets = bindings_by_business.get(str(kpi["id"]), [])
        source = _three_part(model.asset_table(assets[0]), catalog) if assets else "COMPLETAR.catalogo.tabla"
        files[f"databricks/metric_views/{_slug(str(kpi['name']))}.yaml"] = _metric_view_yaml(model, kpi, source)
        coverage.append(_cov("kpi", kpi["name"], "needs_completion", "Metric view (YAML 1.1)",
                             "Completar la expresion SQL agregada de la medida y la tabla fuente."))
    for relation in model.relationships:
        coverage.append(_cov("relationship", relation["name"], "instructions", "Page y instrucciones de Genie",
                             "Si ambos conceptos tienen tabla, declarar el join en el Genie Agent (join_specs)."))
    for prop in model.properties:
        coverage.append(_cov("property", prop["name"], "instructions", "Page del concepto", ""))
    for rule in model.rules:
        coverage.append(_cov("business_rule", rule["name"], "instructions", "Instrucciones del Genie Agent", ""))
    for item in model.synonyms:
        coverage.append(_cov("synonym", item["name"], "native", "Sinonimos de la Page", ""))
    for item in model.constraints:
        coverage.append(_cov("constraint", item["name"], "instructions", "Instrucciones del Genie Agent", ""))

    instructions = _instructions(model)
    files["databricks/genie_workspace_instructions.md"] = instructions
    files["databricks/genie_agent_create_request.json"] = _json(_genie_request(model, settings, tables, instructions))
    files["databricks/README_IMPLEMENTACION.md"] = _databricks_readme(model)
    return files, coverage


def _page_markdown(model: _ReleaseModel, item: dict[str, object], bindings: dict[str, list[dict[str, object]]], catalog: str) -> str:
    item_id = str(item["id"])
    related = [
        str(rel["name"]) for rel in model.relationships if item_id in rel.get("linked_candidate_ids", [])
    ]
    properties = [str(prop["name"]) for prop in model.properties if item_id in prop.get("linked_candidate_ids", [])]
    assets = [_three_part(model.asset_table(asset), catalog) for asset in bindings.get(item_id, [])]
    evidence = dict(item.get("source_binding", {}))
    lines = [
        f"# {item['name']}", "",
        f"**Dominio:** {model.domain}  ",
        f"**Descripcion:** {_one_line(str(item['definition']))}  ",
        f"**Sinonimos:** {', '.join(model.synonyms_for(item_id)) or '-'}", "",
        "## Definicion", "", str(item["definition"]), "",
    ]
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


def _metric_view_yaml(model: _ReleaseModel, kpi: dict[str, object], source: str) -> str:
    synonyms = model.synonyms_for(str(kpi["id"]))[:10]
    lines = [
        "version: 1.1",
        f"source: {source}",
        f"comment: {json.dumps(_one_line(str(kpi['definition'])), ensure_ascii=False)}",
        "measures:",
        f"  - name: {_slug(str(kpi['name'])).replace('-', '_')}",
        '    expr: "COMPLETAR_EXPRESION_AGREGADA"',
        f"    display_name: {json.dumps(str(kpi['name'])[:255], ensure_ascii=False)}",
        f"    comment: {json.dumps(_one_line(str(kpi['definition'])), ensure_ascii=False)}",
    ]
    if synonyms:
        lines.append(f"    synonyms: {json.dumps(synonyms, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def _genie_request(model: _ReleaseModel, settings: dict[str, str], tables: dict[str, str], instructions: str) -> dict[str, object]:
    questions = [
        str(spec.get("example_question")) for spec in model.query_catalog.values() if spec.get("example_question")
    ] or [f"Que es {concept['name']}?" for concept in model.concepts[:5]]
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
                {"identifier": identifier, "description": [_one_line(description)[:1000]]}
                for identifier, description in sorted(tables.items())
            ]
        },
        "instructions": {
            "text_instructions": [{"id": _hex_id(model.release_id, "instructions"), "content": [instructions]}],
        },
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


def _instructions(model: _ReleaseModel) -> str:
    def block(title: str, items: list[dict[str, object]]) -> list[str]:
        if not items:
            return []
        rows = []
        for item in items:
            synonyms = model.synonyms_for(str(item["id"]))
            suffix = f" (sinonimos: {', '.join(synonyms)})" if synonyms else ""
            rows.append(f"- **{item['name']}**{suffix}: {_one_line(str(item['definition']))}")
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
    if not coverage:
        route, reason = "A", "La release no tiene elementos para entregar."
    elif not outside:
        route, reason = "A", "Todo lo aprobado se puede implementar en la plataforma destino."
    elif tables and all(item["status"] == "outside_platform" for item in tables):
        route, reason = "C", (
            f"Ninguna tabla de la release es alcanzable hoy por {TARGET_LABELS[target]}: los datos viven en otros sistemas. "
            f"La definicion se puede cargar, pero sin datos la plataforma no puede responder. Opciones: {BRIDGE_HINTS[target]}"
        )
    else:
        route, reason = "B", (
            f"{outside} elemento(s) dependen de sistemas que la plataforma no alcanza hoy. "
            f"Implementar el resto en {TARGET_LABELS[target]} y resolver esos con un puente o en ONTO (plan B)."
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
        "| Elemento | Nombre | Resultado | Donde queda | Accion |", "| --- | --- | --- | --- | --- |",
    ]
    for item in coverage:
        lines.append(
            f"| {item['element_type']} | {item['name']} | {COVERAGE_LABELS[item['status']]} | {item['target_artifact']} | {item['action'] or '-'} |"
        )
    return "\n".join(lines) + "\n"


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
