"""F4: OWL/Turtle and Ossie exports, and the new Fabric TMDL ontology format."""
from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "tests"))

from test_export_enrichment import _release

from ontology_workbench.platform_exports import build_platform_export

try:
    import rdflib
    from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD
except ImportError:  # pragma: no cover - rdflib is only needed to validate the Turtle
    rdflib = None

OSSIE_TYPES = {"String", "Integer", "Decimal", "Float", "Boolean", "Date", "Time", "DateTime", "DateTimeTz", "Opaque"}


def _release_with_synonym() -> dict:
    release = _release()
    release["canonical_ontology"]["synonyms"] = [
        {"id": "s1", "name": "Cuenta", "definition": "Otro nombre", "owner": "", "linked_candidate_ids": ["cli"]}
    ]
    return release


@unittest.skipIf(rdflib is None, "rdflib no esta instalado")
class TurtleExportTests(unittest.TestCase):
    def setUp(self) -> None:
        text = build_platform_export(_release_with_synonym(), "databricks")["files"]["open_standards/ontology.ttl"]
        self.graph = rdflib.Graph().parse(data=text, format="turtle")

    def _by_label(self, label: str):
        return next(subject for subject, _, value in self.graph.triples((None, RDFS.label, None)) if str(value) == label)

    def test_turtle_is_valid_and_declares_classes_with_labels_comments_and_synonyms(self) -> None:
        cliente = self._by_label("Cliente")
        self.assertIn((cliente, RDF.type, OWL.Class), self.graph)
        self.assertEqual(str(self.graph.value(cliente, RDFS.comment)), "Quien compra")
        self.assertEqual({str(value) for value in self.graph.objects(cliente, SKOS.altLabel)}, {"Cuenta"})

    def test_datatype_properties_have_domain_and_typed_range(self) -> None:
        total = self._by_label("Total")
        self.assertIn((total, RDF.type, OWL.DatatypeProperty), self.graph)
        self.assertEqual(self.graph.value(total, RDFS.domain), self._by_label("Pedido"))
        self.assertEqual(self.graph.value(total, RDFS.range), XSD.double)
        self.assertEqual(self.graph.value(self._by_label("Apodo"), RDFS.range), XSD.string)

    def test_object_properties_link_the_two_concepts(self) -> None:
        relation = self._by_label("Cliente realiza Pedido")
        self.assertIn((relation, RDF.type, OWL.ObjectProperty), self.graph)
        self.assertEqual(self.graph.value(relation, RDFS.domain), self._by_label("Cliente"))
        self.assertEqual(self.graph.value(relation, RDFS.range), self._by_label("Pedido"))

    def test_quotes_in_definitions_do_not_break_the_turtle(self) -> None:
        release = _release()
        release["canonical_ontology"]["concepts"][0]["definition"] = 'Quien "compra"\ny paga \\ siempre'
        text = build_platform_export(release, "fabric")["files"]["open_standards/ontology.ttl"]
        graph = rdflib.Graph().parse(data=text, format="turtle")
        cliente = next(s for s, _, v in graph.triples((None, RDFS.label, None)) if str(v) == "Cliente")
        self.assertEqual(str(graph.value(cliente, RDFS.comment)), 'Quien "compra" y paga \\ siempre')


class OssieExportTests(unittest.TestCase):
    def setUp(self) -> None:
        files = build_platform_export(_release_with_synonym(), "databricks")["files"]
        self.document = json.loads(files["open_standards/semantic_model.ossie.yaml"])

    def test_document_has_the_required_core_fields_of_the_spec(self) -> None:
        self.assertEqual(self.document["version"], "0.3.0.dev0")
        self.assertTrue(self.document["name"])
        datasets = self.document["datasets"]
        self.assertTrue(datasets)
        for dataset in datasets:
            self.assertTrue(dataset["name"] and dataset["source"])
            for field in dataset.get("fields", []):
                self.assertIn("sql", field["expression"])
                self.assertIn(field.get("datatype", "String"), OSSIE_TYPES)

    def test_relationships_reference_declared_datasets_and_fields_with_matching_arity(self) -> None:
        datasets = {dataset["name"]: {field["name"] for field in dataset.get("fields", [])} for dataset in self.document["datasets"]}
        relationships = self.document["relationships"]
        self.assertEqual(len(relationships), 1)
        relation = relationships[0]
        self.assertEqual((relation["from"], relation["to"]), ("pedidos", "clientes"))
        self.assertEqual(len(relation["from_columns"]), len(relation["to_columns"]))
        self.assertTrue(set(relation["from_columns"]) <= datasets[relation["from"]])
        self.assertTrue(set(relation["to_columns"]) <= datasets[relation["to"]])
        clientes = next(dataset for dataset in self.document["datasets"] if dataset["name"] == "clientes")
        self.assertEqual(clientes["primary_key"], ["id"])
        self.assertEqual(clientes["ai_context"], {"synonyms": ["Cuenta"]})

    def test_types_come_from_the_columns_and_no_metric_is_invented(self) -> None:
        pedidos = next(dataset for dataset in self.document["datasets"] if dataset["name"] == "pedidos")
        types = {field["name"]: field["datatype"] for field in pedidos["fields"]}
        self.assertEqual(types["total"], "Decimal")
        self.assertEqual(types["cliente_id"], "Integer")
        self.assertNotIn("metrics", self.document)

    def test_no_ossie_file_without_tables(self) -> None:
        release = _release()
        release["canonical_ontology"]["technical_assets"] = []
        release["canonical_ontology"]["data_bindings"] = []
        files = build_platform_export(release, "fabric")["files"]
        self.assertNotIn("open_standards/semantic_model.ossie.yaml", files)
        self.assertIn("open_standards/ontology.ttl", files)


class PackageIntegrationTests(unittest.TestCase):
    def test_both_platform_packages_include_the_open_standard_files_and_report_them(self) -> None:
        for target in ("fabric", "databricks"):
            export = build_platform_export(_release(), target)
            self.assertEqual(
                export["summary"]["open_standards"],
                ["open_standards/README.md", "open_standards/ontology.ttl", "open_standards/semantic_model.ossie.yaml"],
            )
        readme = export["files"]["open_standards/README.md"]
        self.assertIn("experimental", readme)
        self.assertIn("0.3.0.dev0", readme)

    def test_fabric_tmdl_quotes_names_with_spaces_and_keeps_unreferenced_rules_as_instructions(self) -> None:
        release = _release()
        release["canonical_ontology"]["business_rules"].append(
            {"id": "r2", "name": "Descuento maximo", "definition": "Nunca superar el 30 por ciento.", "source_binding": {}}
        )
        export = build_platform_export(release, "fabric")
        base = "fabric/ontology/ventas_ontology.Ontology"
        self.assertIn("entityRelationship 'Cliente realiza Pedido'\n", export["files"][f"{base}/entityRelationships.tmdl"])
        self.assertIn(f"{base}/rules/Regla_de_anulados.tmdl", export["files"])
        self.assertNotIn(f"{base}/rules/Descuento_maximo.tmdl", export["files"])
        status = {item["name"]: item["status"] for item in export["coverage"] if item["element_type"] == "business_rule"}
        self.assertEqual(status, {"Regla de anulados": "native", "Descuento maximo": "instructions"})
        request = json.loads(export["files"]["fabric/ontology/create_ontology_request.json"])
        paths = {part["path"] for part in request["definition"]["parts"]}
        self.assertTrue({".platform", "database.tmdl", "model.tmdl", "namespaces/default.tmdl"} <= paths)
        model = base64.b64decode(next(part["payload"] for part in request["definition"]["parts"] if part["path"] == "model.tmdl")).decode()
        self.assertIn("ref rule Regla_de_anulados", model)


if __name__ == "__main__":
    unittest.main()
