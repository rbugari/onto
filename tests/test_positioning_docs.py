"""Guards for the repositioning (doc 18): messaging stays consistent and the Argos UI text is translated."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

POSITIONING = "llega a Silver, cruza varios sistemas y lo entrega aprobado, listo para cargar"
ENTRY_DOCS = ["README.md", "docs/10_POSITIONING_AND_BOUNDARIES.md", "docs/OBJETIVO_ALCANCE_Y_FOCO.md"]


class PositioningTests(unittest.TestCase):
    def test_entry_docs_share_the_positioning_phrase(self):
        for relative in ENTRY_DOCS:
            text = (ROOT_DIR / relative).read_text(encoding="utf-8")
            self.assertIn(POSITIONING, text, relative)

    def test_entry_docs_keep_the_no_compete_statement_and_do_not_sell_argos_as_runtime(self):
        for relative in ENTRY_DOCS:
            text = (ROOT_DIR / relative).read_text(encoding="utf-8")
            self.assertIn("no compite", text.lower(), relative)
            self.assertNotIn("runtime de plan B para", text, relative)

    def test_frozen_areas_are_listed_in_one_place(self):
        text = (ROOT_DIR / "docs/00_MVP_OPERATIVO.md").read_text(encoding="utf-8")
        section = text.split("## Congelado", 1)[1].split("\n## ", 1)[0]
        for name in ["runtime.py", "query_catalog.py", "fabric_adapter.py", "mariadb_adapter.py", "local_data_adapter.py"]:
            self.assertIn(name, section)
            self.assertTrue(any(ROOT_DIR.glob(f"src/ontology_workbench/{name}")), f"{name} no existe")

    def test_argos_subtitle_has_translation_and_no_plan_b_wording(self):
        from onto_ui.i18n import EN

        source = (ROOT_DIR / "onto_ui" / "argos.py").read_text(encoding="utf-8")
        match = re.search(r"t\('(Banco de prueba:[^']*)'", source)
        self.assertIsNotNone(match, "subtitulo de Argos no encontrado")
        message = match.group(1)
        self.assertIn(message, EN)
        self.assertNotIn("plan B", message)
        self.assertNotIn("fallback", EN[message].lower())


if __name__ == "__main__":
    unittest.main()
