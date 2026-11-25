"""Discovery with the LLM: realistic sizes, and one unusable relationship must not discard the proposal."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from ontology_workbench.context_scanner import LlmSettings
from ontology_workbench.discovery import MAX_PAYLOAD_CHARS, build_discovery_proposal
from ontology_workbench.models import Concept, OntologyProject, Relation

SETTINGS = LlmSettings("ollama", "test", False)


def _large_project(tables: int = 40, columns: int = 12) -> OntologyProject:
    project = OntologyProject(id="big", name="Big", metadata={"discovery.scope": "Pedidos"})
    for t in range(tables):
        table = Concept(id=f"table-t{t}", name=f"t{t}", tags=["table", "bim"], metadata={"bim.objectType": "table"})
        project.concepts.append(table)
        for c in range(columns):
            column = Concept(
                id=f"column-t{t}-c{c}", name=f"t{t}[col_{c}_{'x' * 120}]", tags=["column", "bim"],
                metadata={"bim.objectType": "column", "bim.table": f"t{t}", "bim.dataType": "varchar(255)", "pad": "y" * 150},
            )
            project.concepts.append(column)
            project.relations.append(Relation(id=f"r-{t}-{c}", source_id=table.id, target_id=column.id, relation_type="contains-column"))
    if tables >= 2:
        project.relations.append(Relation(id="fk", source_id="column-t1-c0", target_id="column-t0-c1", relation_type="bim-relationship"))
    return project


def _response(relationships: list[dict]) -> dict:
    entity = lambda name: {"name": name, "definition": "Definicion", "importance": "core", "reason": "Central",
                           "source_refs": ["s1"], "properties": []}
    return {
        "business_cores": [{"name": "Nucleo", "definition": "Pedidos", "entities": ["Cliente", "Pedido"], "source_refs": ["s1"]}],
        "entities": [entity("Cliente"), entity("Pedido")], "relationships": relationships, "rules": [],
        "business_questions": [], "technical_questions": [], "analytical_questions": [],
    }


def _relation(source: str, target: str, name: str = "r") -> dict:
    return {"name": name, "definition": "Por confirmar", "source": source, "target": target, "source_refs": ["s1"]}


class LargeStructureTests(unittest.TestCase):
    def test_large_structure_is_compacted_into_tables_with_inline_columns(self) -> None:
        project = _large_project()
        with patch("ontology_workbench.discovery.load_llm_settings", return_value=SETTINGS), \
                patch("ontology_workbench.discovery._call_llm", return_value=json.dumps(_response([]))) as call:
            result = build_discovery_proposal(project, [])
        request = call.call_args.args[0][1]["content"]
        self.assertLessEqual(len(request), MAX_PAYLOAD_CHARS)
        payload = json.loads(request)
        tables = [source for source in payload["sources"].values() if source.get("columns")]
        self.assertEqual(len(tables), 40)
        self.assertEqual(len(tables[0]["columns"]), 12)
        self.assertTrue(tables[0]["columns"][0].endswith(":varchar(255)"))
        self.assertEqual([item["type"] for item in payload["relationships"]], ["bim-relationship"])
        self.assertEqual(result["mode"], "model_inference")

    def test_small_structure_keeps_every_object_as_its_own_source(self) -> None:
        project = _large_project(tables=2, columns=3)
        with patch("ontology_workbench.discovery.load_llm_settings", return_value=SETTINGS), \
                patch("ontology_workbench.discovery._call_llm", return_value=json.dumps(_response([]))) as call:
            build_discovery_proposal(project, [])
        payload = json.loads(call.call_args.args[0][1]["content"])
        self.assertEqual(len(payload["sources"]), len(project.concepts))


class RelationshipFilteringTests(unittest.TestCase):
    def _run(self, relationships: list[dict]) -> dict:
        project = _large_project(tables=1, columns=1)
        with patch("ontology_workbench.discovery.load_llm_settings", return_value=SETTINGS), \
                patch("ontology_workbench.discovery._call_llm", return_value=json.dumps(_response(relationships))):
            return build_discovery_proposal(project, [])

    def test_reflexive_and_unknown_relationships_are_discarded_with_a_reason_not_the_whole_proposal(self) -> None:
        result = self._run([_relation("Pedido", "Cliente", "ok"), _relation("Cliente", "Cliente", "reflexiva"), _relation("Pedido", "Fantasma", "desconocida")])
        self.assertEqual([item["name"] for item in result["relationships"]], ["ok"])
        reasons = {item["name"]: item["reason"] for item in result["discarded_relationships"]}
        self.assertEqual(set(reasons), {"reflexiva", "desconocida"})
        self.assertIn("reflexiva", reasons["reflexiva"].lower())

    def test_valid_relationships_leave_no_discard_list(self) -> None:
        self.assertNotIn("discarded_relationships", self._run([_relation("Pedido", "Cliente")]))

    def test_a_malformed_relationship_still_invalidates_the_proposal_and_says_why(self) -> None:
        broken = _relation("Pedido", "Cliente")
        broken["source_refs"] = ["inventado"]
        with self.assertRaisesRegex(ValueError, "propuesta LLM valida .*Referencia invalida"):
            self._run([broken])


class ColumnMappingTests(unittest.TestCase):
    def test_a_known_column_is_kept_and_an_unknown_one_is_dropped_without_failing(self) -> None:
        from ontology_workbench.discovery import _validate_proposal

        response = _response([])
        response["entities"][0]["properties"] = [
            {"name": "Total", "definition": "d", "source_refs": ["s1"], "column": "PEDIDOS.TOTAL"},
            {"name": "Apodo", "definition": "d", "source_refs": ["s1"], "column": "pedidos.inventada"},
        ]
        _validate_proposal(response, {"s1"}, {"pedidos.total": ("pedidos", "total")})
        self.assertEqual([prop.get("column") for prop in response["entities"][0]["properties"]], ["pedidos.total", None])


class DiscoveryAssetsTests(unittest.TestCase):
    DDL = (b"CREATE TABLE clientes (id INT PRIMARY KEY, nombre VARCHAR(80));\n"
           b"CREATE TABLE pedidos (id INT PRIMARY KEY, cliente_id INT, total DECIMAL(10,2), nota VARCHAR(50));\n")

    def setUp(self) -> None:
        from tempfile import TemporaryDirectory

        from ontology_workbench.service import WorkbenchService
        from ontology_workbench.storage import ProjectStore

        self.temp = TemporaryDirectory()
        self.service = WorkbenchService(ProjectStore(Path(self.temp.name) / "projects"))
        self.project = self.service.create_project("Pedidos")
        self.service.import_discovery_file(self.project.id, "esquema.sql", self.DDL)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _draft(self) -> dict:
        # Alias order follows the project objects: s1 clientes, s2-s3 its columns, s4 pedidos.
        response = _response([_relation("Pedido", "Cliente", "Pedido de cliente")])
        response["entities"][0]["source_refs"] = ["s1"]
        response["entities"][1]["source_refs"] = ["s4"]
        response["entities"][1]["properties"] = [
            {"name": "Importe", "definition": "Total del pedido", "source_refs": ["s4"], "column": "pedidos.total"}
        ]
        with patch("ontology_workbench.discovery.load_llm_settings", return_value=SETTINGS), \
                patch("ontology_workbench.discovery._call_llm", return_value=json.dumps(response)):
            return self.service.generate_discovery_draft(self.project.id, "Pedidos")

    def test_draft_attaches_backing_tables_and_mapped_columns_without_adding_review_candidates(self) -> None:
        draft = self._draft()
        self.assertFalse(any(item["candidate_type"] == "technical_asset" for item in draft["candidates"]))
        cliente, pedido = (next(item for item in draft["candidates"] if item["name"] == name) for name in ("Cliente", "Pedido"))
        self.assertEqual({a["name"] for a in cliente["backing_assets"]}, {"clientes", "clientes[id]"})
        self.assertEqual({a["name"] for a in pedido["backing_assets"]}, {"pedidos", "pedidos[id]", "pedidos[cliente_id]"})
        importe = next(item for item in draft["model_elements"] if item["name"] == "Importe")
        self.assertEqual(importe["bound_asset"]["name"], "pedidos[total]")
        self.assertEqual(importe["bound_asset_id"], importe["bound_asset"]["candidate_id"])

    def test_release_and_packages_get_types_bindings_and_joins_from_the_model_citations(self) -> None:
        from ontology_workbench.platform_exports import build_platform_export

        draft = self._draft()
        draft_id = str(draft["manifest"]["draft_id"])
        self.service.bulk_update_nexo_candidates(
            self.project.id, draft_id, [str(item["candidate_id"]) for item in draft["candidates"]], "approved", "R", "Rol", "ok")
        for element in draft["model_elements"]:
            self.service.update_nexo_model_element(self.project.id, draft_id, element["element_id"], "approved", "R", "Rol", "ok")
        release = self.service.publish_nexo_release(self.project.id, draft_id, "R", "n")

        ontology = release["canonical_ontology"]
        self.assertEqual(len(ontology["data_bindings"]), 2)
        self.assertTrue(any(prop.get("bound_asset_id") for prop in ontology["properties"]))
        fabric = build_platform_export(release, "fabric")["files"]
        pedido = next(text for path, text in fabric.items() if path.endswith("entities/Pedido.tmdl"))
        self.assertIn("property Importe\n\t\tdataType: double", pedido)
        databricks = build_platform_export(release, "databricks")
        ossie = json.loads(databricks["files"]["open_standards/semantic_model.ossie.yaml"])
        relation = ossie["relationships"][0]
        self.assertEqual((relation["from"], relation["to"], relation["from_columns"], relation["to_columns"]),
                         ("pedidos", "clientes", ["cliente_id"], ["id"]))
        genie = json.loads(json.loads(databricks["files"]["databricks/genie_agent_create_request.json"])["serialized_space"])
        self.assertNotIn("join_specs", genie["instructions"])  # tables outside Databricks are not joined there


if __name__ == "__main__":
    unittest.main()

