"""F3: platform packages carry types, joins, KPI formula proposals and fuller Pages derived from approved evidence."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from ontology_workbench.export_enrichment import fabric_value_type
from ontology_workbench.platform_exports import build_platform_export


def _asset(asset_id: str, table: str, kind: str = "table", column: str = "", data_type: str = "", **extra: str) -> dict:
    name = table if kind == "table" else f"{table}[{column}]"
    metadata = {"source.platform": "databricks", "bim.objectType": kind, "bim.table": table, **extra}
    if data_type:
        metadata["bim.dataType"] = data_type
    return {"id": asset_id, "name": name, "definition": name, "technical_metadata": metadata}


def _item(item_id: str, name: str, definition: str) -> dict:
    return {"id": item_id, "name": name, "definition": definition, "source_binding": {"source_document_id": "doc-1", "source_chunk_id": "chunk-7"}}


def _release(with_key_column: bool = True) -> dict:
    assets = [
        _asset("t-cli", "clientes"), _asset("t-ped", "pedidos"),
        _asset("c-cli-id", "clientes", "column", "id", "int64"),
        _asset("c-cli-nombre", "clientes", "column", "nombre", "varchar(80)"),
        _asset("c-ped-total", "pedidos", "column", "total", "decimal(10,2)"),
        _asset("m-ventas", "pedidos", "measure", "Ventas", "", **{"bim.expression": "SUM ( pedidos[total] )"}),
    ]
    if with_key_column:
        assets.append(_asset("c-ped-cli", "pedidos", "column", "cliente_id", "int64"))
    def link(element_id: str, name: str, *ids: str, owner: str = "") -> dict:
        return {"id": element_id, "name": name, "definition": f"{name} definido", "owner": owner, "linked_candidate_ids": list(ids)}
    return {
        "manifest": {"release_id": "rel-1", "project_id": "p", "source_assessment": {"scope": {"domain_id": "ventas"}}},
        "canonical_ontology": {
            "concepts": [_item("cli", "Cliente", "Quien compra"), _item("ped", "Pedido", "Compra de un cliente")],
            "kpis": [_item("kpi-v", "Ventas netas", "Suma de pedidos")],
            "business_rules": [_item("r1", "Regla de anulados", "Un Cliente con pedido anulado no cuenta")],
            "technical_assets": assets,
            "properties": [
                link("p1", "Nombre", "cli", owner="Ana"), link("p2", "Total", "ped"), link("p3", "Apodo", "cli"),
            ],
            "relationships": [link("rel", "Cliente realiza Pedido", "cli", "ped")],
            "synonyms": [], "constraints": [],
            "data_bindings": [
                link("b1", "Cliente en clientes", "cli", "t-cli"), link("b2", "Pedido en pedidos", "ped", "t-ped"),
                link("b3", "Total en columna", "ped", "c-ped-total"), link("b4", "KPI en medida", "kpi-v", "m-ventas"),
            ],
        },
        "agent_context_pack": {"query_catalog": {"q": {"example_question": "Cuantos pedidos tiene cada Cliente?"}}},
    }


class ExportEnrichmentTests(unittest.TestCase):
    def test_value_types_map_sql_and_bim_types(self) -> None:
        self.assertEqual(
            [fabric_value_type(item) for item in ("int64", "varchar(80)", "decimal(10,2)", "DateTime", "bit", "geometry")],
            ["BigInt", "String", "Double", "DateTime", "Boolean", None],
        )

    def test_fabric_properties_take_their_type_from_the_bound_column_and_keep_unknowns_for_review(self) -> None:
        files = build_platform_export(_release(), "fabric")["files"]
        entity = next(json.loads(text) for path, text in files.items() if path.endswith("definition.json") and "Cliente" in text and "EntityTypes" in path)
        types = {prop["name"]: prop["valueType"] for prop in entity["properties"]}
        self.assertEqual(types["Nombre"], "String")
        export = build_platform_export(_release(), "fabric")
        status = {item["name"]: item["status"] for item in export["coverage"] if item["element_type"] == "property"}
        self.assertEqual(status, {"Nombre": "native", "Total": "native", "Apodo": "needs_completion"})
        self.assertEqual(export["summary"]["pending_completion"], {"property": 1})

    def test_total_property_is_double_in_fabric(self) -> None:
        files = build_platform_export(_release(), "fabric")["files"]
        pedido = next(json.loads(text) for path, text in files.items() if "EntityTypes" in path and "Pedido" in text)
        self.assertIn("Double", {prop["valueType"] for prop in pedido["properties"]})

    def test_databricks_joins_come_from_the_key_column_in_metric_view_and_genie_agent(self) -> None:
        files = build_platform_export(_release(), "databricks", {"catalog": "main"})["files"]
        metric = files["databricks/metric_views/ventas-netas.yaml"]
        self.assertIn("joins:", metric)
        self.assertIn('"on": source.cliente_id = clientes.id', metric)
        space = json.loads(json.loads(files["databricks/genie_agent_create_request.json"])["serialized_space"])
        join = space["instructions"]["join_specs"][0]
        self.assertEqual(join["left"]["identifier"], "main.default.pedidos")
        self.assertEqual(join["sql"][0], "`pedidos`.`cliente_id` = `clientes`.`id`")
        self.assertIn("main.default.clientes", {table["identifier"] for table in space["data_sources"]["tables"]})

    def test_no_join_is_invented_without_the_key_column(self) -> None:
        files = build_platform_export(_release(with_key_column=False), "databricks")["files"]
        self.assertNotIn("joins:", files["databricks/metric_views/ventas-netas.yaml"])
        space = json.loads(json.loads(files["databricks/genie_agent_create_request.json"])["serialized_space"])
        self.assertNotIn("join_specs", space["instructions"])

    def test_kpi_formula_is_only_a_proposal_and_dax_stays_out_of_databricks(self) -> None:
        fabric = build_platform_export(_release(), "fabric")["files"]
        agent = next(text for path, text in fabric.items() if path.endswith("stage_config.json"))
        self.assertIn("SUM ( pedidos[total] )", agent)
        databricks = build_platform_export(_release(), "databricks")["files"]
        self.assertNotIn("SUM ( pedidos[total] )", databricks["databricks/genie_workspace_instructions.md"])
        metric = databricks["databricks/metric_views/ventas-netas.yaml"]
        self.assertIn("# Propuesta (DAX", metric)
        self.assertIn("COMPLETAR_EXPRESION_AGREGADA", metric)

    def test_page_lists_owner_usage_examples_and_typed_properties(self) -> None:
        page = build_platform_export(_release(), "databricks")["files"]["databricks/pages/cliente.md"]
        self.assertIn("**Responsable:** Ana", page)
        self.assertIn("## Uso de negocio", page)
        self.assertIn("Regla de anulados", page)
        self.assertIn("## Ejemplos", page)
        self.assertIn("Cuantos pedidos tiene cada Cliente?", page)
        self.assertIn("Nombre (nombre, String)", page)
        self.assertIn("doc-1 / chunk-7", page)

    def test_column_comments_and_coverage_report_list_what_is_left_to_complete(self) -> None:
        export = build_platform_export(_release(), "databricks")
        self.assertIn("ALTER COLUMN `total` COMMENT 'Total: Total definido'", export["files"]["databricks/unity_catalog_comments.sql"])
        summary = export["summary"]
        self.assertEqual(summary["pending_completion"], {"kpi": 1})
        self.assertIn("databricks/metric_views/ventas-netas.yaml", summary["placeholders"])
        self.assertIn("## Pendientes de completar", export["files"]["coverage_report.md"])


if __name__ == "__main__":
    unittest.main()
