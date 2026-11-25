"""Consolidation suggestions: same-name assets of different systems are not duplicates and the LLM sees only knowledge."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from ontology_workbench.context_scanner import LlmSettings
from ontology_workbench.nexo_curation import build_consolidation_suggestions


def _candidate(candidate_id: str, kind: str, name: str, source_id: str = "", definition: str = "d") -> dict:
    return {"candidate_id": candidate_id, "candidate_type": kind, "name": name, "definition": definition, "source_id": source_id}


class ConsolidationTests(unittest.TestCase):
    def _suggest(self, candidates: list[dict], llm_response: dict | None = None):
        settings = LlmSettings("ollama", "test", False) if llm_response is not None else LlmSettings("disabled", "", False)
        with patch("ontology_workbench.nexo_curation.load_llm_settings", return_value=settings), \
                patch("ontology_workbench.nexo_curation._call_llm", return_value=json.dumps(llm_response or {"groups": []})) as call:
            return build_consolidation_suggestions(candidates), call

    def test_same_table_in_two_systems_is_not_a_duplicate_but_same_name_concepts_are(self) -> None:
        package, _ = self._suggest([
            _candidate("a1", "technical_asset", "pagos", "legacy"), _candidate("a2", "technical_asset", "pagos", "pedidos"),
            _candidate("c1", "concept", "Pre-pedido"), _candidate("c2", "concept", "Prepedido"),
            _candidate("c3", "concept", "Pre pedido"),
        ])
        groups = [{item["canonical_candidate_id"], *item["duplicate_candidate_ids"]} for item in package["suggestions"]]
        self.assertEqual(groups, [{"c1", "c2", "c3"}])

    def test_the_llm_is_not_asked_about_technical_assets(self) -> None:
        candidates = [_candidate("a1", "technical_asset", "pagos", "legacy"), _candidate("c1", "concept", "Pedido"),
                      _candidate("c2", "concept", "Orden de compra")]
        response = {"groups": [{"canonical_candidate_id": "c1", "duplicate_candidate_ids": ["c2"], "reason": "Mismo concepto"}]}
        package, call = self._suggest(candidates, response)
        sent = call.call_args.args[0][1]["content"]
        self.assertNotIn("pagos", sent)
        self.assertIn("Orden de compra", sent)
        self.assertEqual([item["reason"] for item in package["suggestions"]], ["Mismo concepto"])


if __name__ == "__main__":
    unittest.main()
