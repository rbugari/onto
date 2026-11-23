"""Atlas: data layer (Bronze/Silver/Gold), reach per platform and entities without definition."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from ontology_workbench.data_layers import table_layer
from ontology_workbench.platform_coverage import build_platform_coverage, coverage_gap_texts
from ontology_workbench.platform_reach import recommend_route
from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore

EXAMPLE = ROOT_DIR / "docs" / "casos" / "ventas_distribuidas" / "input"
MARIADB_DDL = b"CREATE TABLE clientes (id INT PRIMARY KEY, nombre VARCHAR(80));\nCREATE TABLE pedidos (id INT PRIMARY KEY, cliente_id INT);\n"


def _table(source_id: str, name: str) -> dict[str, object]:
    return {"source_id": source_id, "name": name, "object_type": "table", "metadata": {}}


def _source(source_id: str, platform: str, layer: str = "") -> dict[str, object]:
    return {"source_id": source_id, "name": source_id, "platform": platform, "platform_label": platform, "layer": layer}


class LayerInferenceTests(unittest.TestCase):
    def test_declared_layer_wins_over_name(self) -> None:
        self.assertEqual(table_layer("silver", "databricks", "gold.fact_ventas"), ("silver", "declared"))

    def test_layer_is_inferred_from_name_markers(self) -> None:
        self.assertEqual(table_layer("", "databricks", "bronze.raw_orders"), ("bronze", "inferred"))
        self.assertEqual(table_layer("", "databricks", "main.stg_clientes"), ("silver", "inferred"))
        self.assertEqual(table_layer("", "databricks", "dim_cliente"), ("gold", "inferred"))

    def test_semantic_models_default_to_gold_and_unmarked_tables_stay_unknown(self) -> None:
        self.assertEqual(table_layer("", "powerbi", "Clientes"), ("gold", "inferred"))
        self.assertEqual(table_layer("", "mariadb", "clientes"), ("unknown", "unknown"))


class PlatformCoverageTests(unittest.TestCase):
    def test_route_is_a_b_or_c_by_reachable_tables(self) -> None:
        self.assertEqual(recommend_route("fabric", 4, 0, 4, 0)[0], "A")
        self.assertEqual(recommend_route("fabric", 4, 1, 4, 1)[0], "B")
        self.assertEqual(recommend_route("fabric", 4, 4, 4, 4)[0], "C")

    def test_each_platform_reaches_only_its_own_ecosystem(self) -> None:
        sources = [_source("lake", "databricks"), _source("bi", "powerbi"), _source("erp", "mariadb")]
        objects = [_table("lake", "silver_clientes"), _table("bi", "Clientes"), _table("erp", "clientes")]

        coverage = build_platform_coverage(sources, objects, None)

        rows = {row["source_id"]: row for row in coverage["sources"]}
        self.assertTrue(rows["lake"]["reachable_by"]["databricks"]["reachable"])
        self.assertFalse(rows["lake"]["reachable_by"]["fabric"]["reachable"])
        self.assertTrue(rows["bi"]["reachable_by"]["fabric"]["reachable"])
        self.assertTrue(rows["erp"]["reachable_by"]["fabric"]["bridge"])
        self.assertEqual(coverage["routes"]["fabric"]["route"], "B")
        self.assertEqual(coverage["routes"]["databricks"]["route"], "B")

    def test_entities_below_gold_without_definition_open_a_gap_only_with_business_context(self) -> None:
        sources = [_source("lake", "databricks")]
        objects = [_table("lake", "silver_clientes"), _table("lake", "gold.dim_producto")]

        self.assertEqual(coverage_gap_texts(build_platform_coverage(sources, objects, None)), [])

        context = {"definitions": [{"term": "Producto", "definition": "Articulo vendido"}]}
        gaps = {gap["code"]: gap for gap in coverage_gap_texts(build_platform_coverage(sources, objects, context))}
        self.assertEqual(set(gaps), {"entities-without-definition-below-gold"})
        self.assertIn("cliente", gaps["entities-without-definition-below-gold"]["message"])

        context["definitions"].append({"term": "Cliente", "definition": "Quien compra"})
        self.assertEqual(coverage_gap_texts(build_platform_coverage(sources, objects, context)), [])


class AtlasAssessmentCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.service = WorkbenchService(ProjectStore(Path(self.temp_dir.name) / "projects"))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_distributed_domain_is_route_b_in_both_platforms_and_report_explains_it(self) -> None:
        project = self.service.create_project("Distribuido")
        for item in json.loads((EXAMPLE / "scope.json").read_text(encoding="utf-8"))["sources"]:
            source = self.service.register_data_source(project.id, item["name"], item["platform"], item["owner"])
            if item["file"]:
                path = EXAMPLE / item["file"]
                self.service.import_source_metadata_file(project.id, source.source_id, path.name, path.read_bytes())

        package = self.service.create_atlas_assessment(project.id, "Client", "Sales", "Product")

        routes = package["platform_coverage"]["routes"]
        self.assertEqual({target: route["route"] for target, route in routes.items()}, {"fabric": "B", "databricks": "B"})
        self.assertIn("platform_coverage.json", package["manifest"]["artifacts"])
        details = self.service.get_atlas_assessment(project.id, str(package["manifest"]["run_id"]))
        self.assertEqual(details["platform_coverage"]["routes"], routes)
        self.assertIn("## Que entiende hoy la plataforma", details["execution_summary"])

    def test_single_mariadb_system_is_route_c_for_both_platforms(self) -> None:
        project = self.service.create_project("Legacy")
        erp = self.service.register_data_source(project.id, "ERP", "mariadb", owner="Sistemas")
        self.service.import_source_metadata_file(project.id, erp.source_id, "erp.sql", MARIADB_DDL)

        package = self.service.create_atlas_assessment(project.id, "Client", "Sales", "Product")

        routes = package["platform_coverage"]["routes"]
        self.assertEqual({target: route["route"] for target, route in routes.items()}, {"fabric": "C", "databricks": "C"})

    def test_declared_layer_is_saved_validated_and_marked_as_declared(self) -> None:
        project = self.service.create_project("Capas")
        lake = self.service.register_data_source(project.id, "Lake", "databricks", owner="Datos", layer="silver")
        self.service.import_source_metadata_file(project.id, lake.source_id, "lake.sql", MARIADB_DDL)

        with self.assertRaises(ValueError):
            self.service.update_data_source(project.id, lake.source_id, "Lake", "databricks", layer="platinum")
        package = self.service.create_atlas_assessment(project.id, "Client", "Sales", "Product")

        row = package["platform_coverage"]["sources"][0]
        self.assertEqual(row["layers"], {"silver": 2})
        self.assertEqual(row["layer_source"], "declared")
        self.service.update_data_source(project.id, lake.source_id, "Lake", "databricks", layer="")
        self.assertEqual(self.service.list_data_sources(project.id)[0].layer, "")


if __name__ == "__main__":
    unittest.main()
