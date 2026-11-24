"""Fixes found by running ONTO on real repositories: code blocks in docs and empty-ontology warnings."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "tests"))

from test_export_enrichment import _release

from ontology_workbench.context_scanner import build_business_context_inventory, build_document_chunks
from ontology_workbench.models import DocumentRecord, OntologyProject
from ontology_workbench.platform_exports import build_platform_export

DOC = """# Flujo de pedidos

Cliente: persona que compra.

```mermaid
sequenceDiagram
    A->>API: Decodificar JWT
    API->>DB: Validar usuario existe
    Note over A: IMPORTANTE: no guardar el token
```

Pedido: solicitud de compra de un cliente.

~~~yaml
clave: valor de configuracion
~~~

Factura: documento que respalda la venta.
"""


def _inventory(chunk_size: int, overlap: int) -> dict:
    document = DocumentRecord("doc-1", "p", "flujo.md", "", "functional_docs", "text/markdown", "now", "extracted")
    chunks = build_document_chunks([document], {"doc-1": DOC}, chunk_size=chunk_size, overlap=overlap)
    with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}):
        return build_business_context_inventory(OntologyProject("p", "P"), [document], {"doc-1": DOC}, chunks=chunks)


class CodeBlockTests(unittest.TestCase):
    def test_bold_markers_do_not_leak_into_terms_and_definitions(self) -> None:
        document = DocumentRecord("doc-2", "p", "db.md", "", "functional_docs", "text/markdown", "now", "extracted")
        text = "**Motor:** MySQL 8.0+ / MariaDB\n**Tabla:** `clientes`\n"
        chunks = build_document_chunks([document], {"doc-2": text})
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}):
            inventory = build_business_context_inventory(OntologyProject("p", "P"), [document], {"doc-2": text}, chunks=chunks)
        self.assertEqual(
            {(item["term"], item["definition"]) for item in inventory["definitions"]},
            {("Motor", "MySQL 8.0+ / MariaDB"), ("Tabla", "clientes")},
        )
    def test_terms_in_fenced_blocks_are_not_business_definitions(self) -> None:
        terms = {item["term"] for item in _inventory(6_000, 500)["definitions"]}
        self.assertEqual(terms, {"Cliente", "Pedido", "Factura"})

    def test_chunks_that_start_inside_a_block_are_still_filtered(self) -> None:
        for size in (90, 130, 170, 210):
            terms = {item["term"] for item in _inventory(size, 60)["definitions"]}
            self.assertFalse(terms & {"A->>API", "API->>DB", "IMPORTANTE", "Note over A", "clave"}, f"chunk_size={size}: {terms}")
            self.assertIn("Pedido", terms)


class EmptyOntologyWarningTests(unittest.TestCase):
    def test_release_without_concepts_warns_in_summary_and_report(self) -> None:
        release = _release()
        release["canonical_ontology"]["concepts"] = []
        for target in ("fabric", "databricks"):
            export = build_platform_export(release, target)
            self.assertEqual(len(export["summary"]["warnings"]), 1)
            self.assertIn("sin entidades", export["files"]["coverage_report.md"])

    def test_release_with_concepts_has_no_warning(self) -> None:
        self.assertEqual(build_platform_export(_release(), "fabric")["summary"]["warnings"], [])


if __name__ == "__main__":
    unittest.main()
