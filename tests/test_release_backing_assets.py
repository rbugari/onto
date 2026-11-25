"""Release adopts the tables behind approved entities and the column mapped by approved properties."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from ontology_workbench.nexo import build_ontology_release
from ontology_workbench.platform_exports import build_platform_export


def _asset(candidate_id: str, name: str, kind: str, **metadata: str) -> dict:
    return {
        "candidate_id": candidate_id, "candidate_type": "technical_asset", "name": name, "definition": f"Activo {name}",
        "status": "pending_review", "confidence": 1.0, "source_id": "db",
        "technical_metadata": {"bim.objectType": kind, "source.platform": "databricks", **metadata},
        "evidence": {"source_document_id": "source:db", "source_chunk_id": f"source:db:{name}", "source_excerpt": name},
    }


def _draft(approve_property: bool = True) -> dict:
    clientes = _asset("t-cli", "clientes", "table")
    key = _asset("c-cli-id", "clientes[id]", "column", **{"bim.table": "clientes", "bim.dataType": "bigint(20)"})
    total = _asset("c-ped-total", "pedidos[total]", "column", **{"bim.table": "pedidos", "bim.dataType": "decimal(10,2)"})
    entity = {
        "candidate_id": "cli", "candidate_type": "concept", "name": "Cliente", "definition": "Quien compra", "status": "approved",
        "confidence": 0.0, "backing_assets": [clientes, key],
        "evidence": {"source_document_id": "", "source_chunk_id": "", "source_excerpt": "", "evidence_status": "inferred"},
    }
    prop = {
        "element_id": "p1", "element_type": "property", "name": "Importe", "definition": "Total", "owner": "",
        "linked_candidate_ids": ["cli"], "status": "approved" if approve_property else "rejected",
        "bound_asset_id": "c-ped-total", "bound_asset": total, "decision": None,
    }
    return {
        "manifest": {"draft_id": "d", "project_id": "p", "source_assessment": {"scope": {"domain_id": "ventas"}}},
        "candidates": [entity], "model_elements": [prop], "review_decisions": [], "model_element_decisions": [],
    }


class BackingAssetTests(unittest.TestCase):
    def test_approved_entity_brings_its_tables_and_a_binding_and_property_its_column(self) -> None:
        ontology = build_ontology_release(_draft(), "rel-1", "R", "n")["canonical_ontology"]
        self.assertEqual({asset["name"] for asset in ontology["technical_assets"]}, {"clientes", "clientes[id]", "pedidos[total]"})
        self.assertEqual([binding["name"] for binding in ontology["data_bindings"]], ["Cliente en clientes"])
        self.assertEqual(ontology["data_bindings"][0]["linked_candidate_ids"], ["cli", "t-cli"])
        self.assertEqual(ontology["properties"][0]["bound_asset_id"], "c-ped-total")

    def test_a_property_that_is_not_approved_does_not_bring_its_column(self) -> None:
        names = {asset["name"] for asset in build_ontology_release(_draft(False), "rel-1", "R", "n")["canonical_ontology"]["technical_assets"]}
        self.assertNotIn("pedidos[total]", names)

    def test_packages_use_the_explicit_column_link_even_when_names_differ(self) -> None:
        release = build_ontology_release(_draft(), "rel-1", "R", "n")
        entity = build_platform_export(release, "fabric")["files"]["fabric/ontology/ventas_ontology.Ontology/entities/Cliente.tmdl"]
        self.assertIn("property Importe\n\t\tdataType: double", entity)


if __name__ == "__main__":
    unittest.main()
