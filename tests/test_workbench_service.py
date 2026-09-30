from __future__ import annotations

import base64
import re
import sys
import unittest
import json
import io
import os
import zipfile
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore, unique_file_paths_by_content
from ontology_workbench.context_scanner import CONTEXT_CHUNK_SIZE, build_document_chunks, load_llm_settings
from ontology_workbench.nexo_diff import compare_nexo_artifacts
from ontology_workbench.nexo import build_registry_draft
from ontology_workbench.fabric_adapter import execute_fabric_read_only_query, load_fabric_settings
from ontology_workbench.runtime import (
    fabric_query_parameters,
    investigate_context_pack_with_llm,
    investigate_context_pack,
    select_fabric_query,
)
from ontology_workbench.query_catalog import (
    catalog_for_context,
    extract_query_parameters,
    normalize_query_catalog,
    ordered_query_parameters,
    select_catalog_query,
)
from ontology_workbench.mariadb_schema import parse_mariadb_schema_dump
from ontology_workbench.external_metadata import parse_columns_csv, parse_sql_ddl
from ontology_workbench.platform_exports import build_platform_export
from ontology_workbench.result_views import infer_visualization, starter_questions
from ontology_workbench.runtime_evaluation import parse_evaluation_cases
from ontology_workbench.query_catalog import LEGACY_FABRIC_QUERY_CATALOG
from ontology_workbench.mariadb_adapter import (
    MARIADB_QUERY_TEMPLATES,
    execute_mariadb_read_only_query,
)
from ontology_workbench.semantic_model_importer import parse_tmdl_text


class WorkbenchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.store = ProjectStore(Path(self.temp_dir.name) / "projects")
        self.service = WorkbenchService(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_project_persists_json_file(self) -> None:
        project = self.service.create_project("Customer Master")

        self.assertTrue(self.store.project_exists(project.id))
        loaded = self.service.get_project(project.id)
        self.assertEqual(loaded.name, "Customer Master")
        self.assertEqual(loaded.description, "")

    def test_tmdl_import_reuses_semantic_model_contract(self) -> None:
        project = self.service.create_project("TMDL")
        content = (
            "model Model\n"
            "    culture: es-ES\n"
            "table 'Sales'\n"
            "    column 'Amount'\n"
            "        dataType: decimal\n"
            "    measure 'Revenue' = SUM(Sales[Amount])\n"
            "table 'Products'\n"
            "    column 'Id'\n"
            "        dataType: int64\n"
            "relationship sales-products\n"
            "    fromColumn: Sales.ProductId\n"
            "    toColumn: Products.Id\n"
        ).encode("utf-8")

        payload = parse_tmdl_text(content.decode("utf-8"))
        imported, summary = self.service.import_semantic_model_file(
            project.id, "model.tmdl", content
        )

        self.assertEqual(payload["model"]["culture"], "es-ES")
        self.assertEqual(summary["tables"], 2)
        self.assertEqual(summary["columns"], 2)
        self.assertEqual(summary["measures"], 1)
        self.assertEqual(summary["relationships"], 1)
        self.assertEqual(imported.metadata["source.format"], "tmdl")
        self.assertTrue(any(concept.name == "Sales[Amount]" for concept in imported.concepts))

    def test_pbip_zip_import_reads_tmdl_without_extracting_paths(self) -> None:
        project = self.service.create_project("PBIP")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr(
                "Sales.SemanticModel/definition/tables/Sales.tmdl",
                "table Sales\n    column Id\n        dataType: int64\n",
            )

        imported, summary = self.service.import_semantic_model_file(
            project.id, "sales.pbip", archive.getvalue()
        )

        self.assertEqual(summary["tables"], 1)
        self.assertEqual(summary["columns"], 1)
        self.assertEqual(imported.metadata["source.format"], "pbip")

    def test_semantic_model_api_payload_reuses_canonical_contract(self) -> None:
        project = self.service.create_project("Semantic API")
        payload = {
            "semanticModel": {
                "culture": "es-ES",
                "tables": [
                    {
                        "name": "Sales",
                        "columns": [{"name": "Amount", "dataType": "decimal"}],
                        "measures": [{"name": "Revenue", "expression": "SUM(Sales[Amount])"}],
                    }
                ],
                "relationships": [],
            }
        }

        imported, summary = self.service.import_semantic_model_api_payload(
            project.id, payload, endpoint_label="fabric-semantic-model"
        )

        self.assertEqual(summary["tables"], 1)
        self.assertEqual(summary["columns"], 1)
        self.assertEqual(summary["measures"], 1)
        self.assertEqual(imported.metadata["source.format"], "semantic-model-api")
        self.assertEqual(imported.metadata["source.api.endpoint"], "fabric-semantic-model")

    def test_semantic_model_api_payload_rejects_missing_tables(self) -> None:
        project = self.service.create_project("Invalid Semantic API")

        with self.assertRaisesRegex(ValueError, "lista de tablas"):
            self.service.import_semantic_model_api_payload(project.id, {"model": {}})

    def test_runtime_investigation_persists_audit_metadata_without_secrets(self) -> None:
        project = self.service.create_project("Audit")
        investigation = {
            "manifest": {
                "release_id": "release-audit",
                "investigation_id": "investigation-audit",
                "created_at": "2026-08-13T12:00:00+00:00",
                "status": "answered",
            },
            "request": {"question": "Cuantos pedidos hay?"},
            "retrieval": [],
            "answer": "Hay 4 pedidos.",
            "llm_used": False,
            "live_query": {
                "query_name": "order_status_summary",
                "operation": "SELECT",
                "status": "connected_read_only_query",
                "rows": [{"estado": "abierto", "cantidad": 4}],
            },
        }

        run_dir = self.store.save_runtime_investigation(project.id, investigation)
        audit = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
        loaded = self.store.load_runtime_investigation(
            project.id, "release-audit", "investigation-audit"
        )

        self.assertEqual(audit["project_id"], project.id)
        self.assertEqual(audit["query_name"], "order_status_summary")
        self.assertEqual(audit["operation"], "SELECT")
        self.assertEqual(audit["row_count"], 1)
        self.assertFalse(audit["secrets_persisted"])
        self.assertNotIn("Cuantos pedidos hay?", json.dumps(audit))
        self.assertEqual(loaded["audit"], audit)

    def test_runtime_retention_report_only_marks_old_investigations(self) -> None:
        project = self.service.create_project("Retention")
        for index, created_at in enumerate(
            (
                "2026-08-13T10:00:00+00:00",
                "2026-08-13T11:00:00+00:00",
                "2026-08-13T12:00:00+00:00",
            ),
            start=1,
        ):
            self.store.save_runtime_investigation(
                project.id,
                {
                    "manifest": {
                        "release_id": "release-retention",
                        "investigation_id": f"investigation-{index}",
                        "created_at": created_at,
                        "status": "answered",
                    },
                    "request": {"question": f"Pregunta {index}"},
                    "retrieval": [],
                    "answer": "ok",
                },
            )

        report = self.service.runtime_retention_report(
            project.id, "release-retention", keep_latest=2
        )

        self.assertEqual(report["total_investigations"], 3)
        self.assertEqual(report["retained_ids"], ["investigation-3", "investigation-2"])
        self.assertEqual(report["candidate_ids"], ["investigation-1"])
        self.assertFalse(report["deletion_performed"])
        self.assertTrue(
            (Path(self.temp_dir.name) / "runtime" / project.id / "release-retention" / "investigation-1").exists()
        )

    def test_investigate_release_accepts_normalized_release_path_id(self) -> None:
        project = self.service.create_project("Runtime release")
        release_id = "release-2026-08-11T07-54-06-00-00-test"
        release = {
            "manifest": {"project_id": project.id, "release_id": release_id, "created_at": "2026-08-11T07:54:06+00:00"},
            "canonical_ontology": {},
            "review_decisions": [],
            "evidence_index": {},
            "source_bindings": [],
            "agent_context_pack": {
                "entities": [],
                "rules": [],
                "kpis": [],
                "bindings": [],
                "query_contract": {
                    "allowed_operations": ["SELECT"],
                    "disallowed_operations": ["INSERT", "UPDATE", "DELETE", "DDL"],
                    "requires_approved_data_binding": True,
                },
            },
            "interoperability_mappings": {},
        }
        self.store.save_nexo_release(project.id, release)

        with patch(
            "ontology_workbench.service.load_llm_settings",
            return_value=SimpleNamespace(enabled=False, provider="", model=""),
        ), patch(
            "ontology_workbench.service.investigate_context_pack"
        ) as investigate, patch.object(self.store, "save_runtime_investigation", return_value=Path("runtime-test")):
            investigate.return_value = {
                "manifest": {
                    "status": "answered",
                    "release_id": release_id,
                    "investigation_id": "investigation-test",
                },
                "answer": "ok",
            }
            result = self.service.investigate_release(
                project.id,
                release_id.lower(),
                "What is the status?",
            )

        investigate.assert_called_once()
        self.assertEqual(result["answer"], "ok")

    def test_fabric_adapter_uses_external_shared_configuration_without_copying_it(self) -> None:
        shared_env = Path(self.temp_dir.name) / "shared-fabric.env"
        shared_env.write_text(
            "\n".join(
                [
                    "FABRIC_AUTH_MODE=interactive_browser",
                    "FABRIC_AUTH_METHOD=interactive_browser",
                    "FABRIC_WAREHOUSE_SERVER=test.fabric.microsoft.com",
                    "FABRIC_WAREHOUSE_DATABASE=test_warehouse",
                    "FABRIC_TENANT_ID=tenant-id",
                    "FABRIC_CLIENT_ID=client-id",
                ]
            ),
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"ONTO_FABRIC_CONFIG_PATH": str(shared_env)}, clear=False):
            settings = load_fabric_settings()

        self.assertEqual(settings.server, "test.fabric.microsoft.com")
        self.assertEqual(settings.database, "test_warehouse")
        self.assertEqual(settings.auth_record_path, shared_env.parent / "data" / "fabric-auth-record.json")

    def test_fabric_query_gateway_accepts_named_read_only_queries_only(self) -> None:
        with self.assertRaisesRegex(ValueError, "Consulta Fabric no soportada"):
            execute_fabric_read_only_query("select * from gold_sic.fact_riesgo")

        with patch("ontology_workbench.service.execute_fabric_read_only_query") as execute_query:
            execute_query.return_value = {
                "status": "connected_read_only_query",
                "query_name": "risk_summary",
                "operation": "SELECT",
                "rows": [{"total_rows": 1}],
            }
            result = self.service.execute_fabric_validation_query("risk_summary")

        execute_query.assert_called_once_with("risk_summary")
        self.assertEqual(result["operation"], "SELECT")

    def test_fabric_rule_query_requires_two_integer_parameters(self) -> None:
        with self.assertRaisesRegex(ValueError, "requiere id_risc y sic enteros"):
            execute_fabric_read_only_query("risk_rule_sic", ("1003", 12))

    def test_fabric_metadata_becomes_atlas_technical_evidence_without_business_rows(self) -> None:
        project = self.service.create_project("Fabric Atlas")
        discovery = {
            "project_id": project.id,
            "server": "test.fabric.microsoft.com",
            "database": "warehouse",
            "tables": [{"schema": "dbo", "name": "Customer", "type": "BASE TABLE"}],
            "columns": [
                {"schema": "dbo", "table": "Customer", "name": "CustomerId", "data_type": "int", "nullable": "NO"},
                {"schema": "dbo", "table": "Customer", "name": "Name", "data_type": "varchar", "nullable": "YES"},
            ],
        }
        package_path = self.store.save_fabric_discovery(project.id, "fabric-test", discovery)
        discovery["package_path"] = str(package_path)

        first_import = self.service.import_fabric_metadata(project.id, discovery)
        second_import = self.service.import_fabric_metadata(project.id, discovery)
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Sales", "Customer")

        self.assertEqual(first_import["added"], 3)
        self.assertEqual(second_import["added"], 0)
        self.assertEqual(assessment["semantic_inventory"]["summary"]["tables"], 1)
        self.assertEqual(assessment["semantic_inventory"]["summary"]["columns"], 2)
        self.assertEqual(
            len([relation for relation in self.service.get_project(project.id).relations if relation.relation_type == "contains-column"]),
            2,
        )
        technical_source = assessment["source_inventory"]["technical_sources"][0]
        self.assertEqual(technical_source["source_format"], "fabric-information-schema")
        self.assertTrue(technical_source["content_sha256"])
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))
        self.assertEqual(
            len([item for item in draft["candidates"] if item["candidate_type"] == "technical_asset"]),
            3,
        )

        documentation_draft = self.service.create_nexo_draft(
            project.id, str(assessment["manifest"]["run_id"]), source_authority="documentation"
        )
        self.assertEqual(documentation_draft["manifest"]["source_authority"], "documentation")
        self.assertGreater(
            len([item for item in documentation_draft["candidates"] if item["candidate_type"] == "technical_asset"]),
            0,
        )

    def test_nexo_rejects_unknown_source_authority(self) -> None:
        project = self.service.create_project("Authority")
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")

        with self.assertRaisesRegex(ValueError, "source_authority"):
            self.service.create_nexo_draft(
                project.id, str(assessment["manifest"]["run_id"]), source_authority="unknown"
            )

    def test_documentation_first_matches_assets_and_records_unbound_gaps(self) -> None:
        project = self.service.create_project("Documentation bindings")
        draft = build_registry_draft(
            project,
            {
                "run_id": "atlas-test",
                "created_at": "2026-08-11T00:00:00+00:00",
                "scope": {"project_id": project.id},
            },
            {
                "definitions": [
                    {
                        "term": "Riesgo consolidado",
                        "definition": "Se publica en gold_sic.fact_riesgo.",
                        "source_document_id": "doc-1",
                        "source_chunk_id": "doc-1-chunk-1",
                        "source_excerpt": "gold_sic.fact_riesgo",
                    },
                    {
                        "term": "Concepto sin binding",
                        "definition": "El esquema gold_sic no identifica un activo concreto.",
                        "source_document_id": "doc-1",
                        "source_chunk_id": "doc-1-chunk-2",
                        "source_excerpt": "El esquema gold_sic no identifica un activo concreto.",
                    },
                ]
            },
            {
                "objects": [
                    {
                        "name": "fact_riesgo",
                        "source_ref": "gold_sic.fact_riesgo",
                        "metadata": {
                            "fabric.objectType": "table",
                            "fabric.schema": "gold_sic",
                            "fabric.table": "fact_riesgo",
                        },
                    }
                ]
            },
            "draft-test",
            source_authority="documentation",
        )

        matches = draft["manifest"]["authority_review"]["matches"]
        gaps = draft["manifest"]["authority_review"]["gaps"]
        matched = next(item for item in matches if item["candidate_type"] == "concept" and item["status"] == "matched")
        self.assertEqual(matched["technical_asset_ids"], ["candidate-technical-asset-0003"])
        self.assertEqual(len(gaps), 1)
        unbound = next(item for item in draft["candidates"] if item["name"] == "Concepto sin binding")
        self.assertEqual(unbound["technical_match"]["status"], "unmatched")

        draft_path = self.store.save_nexo_draft(draft)
        result = self.service.propose_nexo_source_bindings(project.id, "draft-test")
        self.assertEqual(result["created"], 1)
        stored = self.service.get_nexo_draft(project.id, "draft-test")
        self.assertEqual(stored["model_elements"][0]["element_type"], "source_binding")
        self.assertEqual(stored["model_elements"][0]["status"], "pending_review")

    def test_add_concept_assigns_incremental_unique_ids(self) -> None:
        project = self.service.create_project("Semantic Model")

        project = self.service.add_concept(project.id, "Customer")
        project = self.service.add_concept(project.id, "Customer")

        self.assertEqual([concept.id for concept in project.concepts], ["customer", "customer-2"])

    def test_add_relation_requires_existing_concepts(self) -> None:
        project = self.service.create_project("Graph")
        project = self.service.add_concept(project.id, "Account")
        project = self.service.add_concept(project.id, "Invoice")

        project = self.service.add_relation(project.id, "account", "invoice", "feeds")

        self.assertEqual(len(project.relations), 1)
        self.assertEqual(project.relations[0].relation_type, "feeds")

    def test_metadata_roundtrip(self) -> None:
        project = self.service.create_project("Stewardship")

        updated = self.service.update_metadata(project.id, {"owner": "data-office", "domain": "finance"})

        reloaded = self.service.get_project(updated.id)
        self.assertEqual(reloaded.metadata["owner"], "data-office")
        self.assertEqual(reloaded.metadata["domain"], "finance")

    def test_create_snapshot_and_restore_previous_state(self) -> None:
        project = self.service.create_project("Lifecycle")
        project = self.service.add_concept(project.id, "Source")
        snapshot = self.service.create_snapshot(project.id, note="baseline")

        self.service.add_concept(project.id, "Target")
        restored = self.service.restore_snapshot(project.id, snapshot.snapshot_id)

        self.assertEqual([concept.name for concept in restored.concepts], ["Source"])
        self.assertEqual(self.service.list_snapshots(project.id)[0].note, "baseline")

    def test_export_and_import_project_roundtrip(self) -> None:
        project = self.service.create_project("Portability")
        project = self.service.add_concept(project.id, "Customer", definition="Business entity")
        project = self.service.add_concept(project.id, "Order")
        self.service.add_relation(project.id, "customer", "order", "owns")

        payload = self.service.export_project_json(project.id)
        imported = self.service.import_project(json.loads(payload))

        self.assertEqual(imported.name, "Portability")
        self.assertNotEqual(imported.id, project.id)
        self.assertEqual(len(imported.concepts), 2)

    def test_validate_project_reports_duplicate_names_and_self_relations(self) -> None:
        project = self.service.create_project("Quality")
        project = self.service.add_concept(project.id, "Customer")
        project = self.service.add_concept(project.id, "Customer")
        project = self.service.add_relation(project.id, "customer", "customer", "same-as")

        issues = self.service.validate_project(project.id)
        issue_codes = {issue.code for issue in issues}

        self.assertIn("duplicate-concept-name", issue_codes)
        self.assertIn("self-relation", issue_codes)
        self.assertIn("missing-definition", issue_codes)

    def test_update_and_delete_concept_cascade_relations(self) -> None:
        project = self.service.create_project("Maintenance")
        project = self.service.add_concept(project.id, "Customer")
        project = self.service.add_concept(project.id, "Order")
        project = self.service.add_relation(project.id, "customer", "order", "owns")

        project = self.service.update_concept(
            project.id,
            concept_id="customer",
            name="Client",
            definition="Paying entity",
            status="approved",
            tags=["gold"],
        )
        self.assertEqual(project.concepts[0].name, "Client")
        self.assertEqual(project.concepts[0].status, "approved")

        project = self.service.delete_concept(project.id, "customer")
        self.assertEqual(len(project.concepts), 1)
        self.assertEqual(len(project.relations), 0)

    def test_update_and_delete_relation(self) -> None:
        project = self.service.create_project("Relationship")
        project = self.service.add_concept(project.id, "Customer")
        project = self.service.add_concept(project.id, "Order")
        project = self.service.add_relation(project.id, "customer", "order", "owns")

        project = self.service.update_relation(
            project.id,
            relation_id="customer-owns-order",
            source_id="order",
            target_id="customer",
            relation_type="belongs-to",
            description="reverse view",
        )
        self.assertEqual(project.relations[0].relation_type, "belongs-to")
        self.assertEqual(project.relations[0].source_id, "order")

        project = self.service.delete_relation(project.id, "customer-owns-order")
        self.assertEqual(len(project.relations), 0)

    def test_import_bim_model_populates_project_with_tabular_objects(self) -> None:
        project = self.service.create_project("Risk1")
        bim_payload = {
            "model": {
                "culture": "es-AR",
                "compatibilityLevel": 1601,
                "tables": [
                    {
                        "name": "DimCustomer",
                        "columns": [
                            {"name": "CustomerKey", "dataType": "int64"},
                            {"name": "CustomerName", "dataType": "string"},
                        ],
                        "measures": [
                            {"name": "Customer Count", "expression": "COUNTROWS(DimCustomer)"}
                        ],
                    },
                    {
                        "name": "FactSales",
                        "columns": [
                            {"name": "CustomerKey", "dataType": "int64"},
                            {"name": "Amount", "dataType": "decimal"},
                        ],
                    },
                ],
                "relationships": [
                    {
                        "fromTable": "FactSales",
                        "fromColumn": "CustomerKey",
                        "toTable": "DimCustomer",
                        "toColumn": "CustomerKey",
                        "isActive": True,
                    }
                ],
            }
        }

        imported, summary = self.service.import_bim_model(project.id, bim_payload, clear_existing=True)

        concept_names = {concept.name for concept in imported.concepts}
        relation_types = {relation.relation_type for relation in imported.relations}
        self.assertIn("DimCustomer", concept_names)
        self.assertIn("DimCustomer[CustomerKey]", concept_names)
        self.assertIn("DimCustomer[Customer Count]", concept_names)
        self.assertIn("contains-column", relation_types)
        self.assertIn("contains-measure", relation_types)
        self.assertIn("bim-relationship", relation_types)
        self.assertEqual(summary["tables"], 2)
        self.assertEqual(summary["columns"], 4)
        self.assertEqual(summary["measures"], 1)
        self.assertEqual(summary["relationships"], 1)

    def test_import_bim_file_retains_technical_source_for_atlas(self) -> None:
        project = self.service.create_project("Bim Evidence")
        content = json.dumps(
            {"model": {"tables": [{"name": "DimDate", "columns": [{"name": "Date", "dataType": "dateTime"}]}]}}
        ).encode("utf-8")

        imported, _ = self.service.import_bim_file(project.id, "semantic-model.bim", content)
        package = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")

        self.assertEqual(imported.metadata["source.technical.filename"], "semantic-model.bim")
        self.assertTrue(Path(imported.metadata["source.technical.path"]).exists())
        technical_sources = package["source_inventory"]["technical_sources"]
        self.assertEqual(len(technical_sources), 1)
        self.assertEqual(technical_sources[0]["content_sha256"], imported.metadata["source.technical.sha256"])
        self.assertNotIn(
            "missing-technical-source-evidence",
            {gap["gap_id"] for gap in package["gap_backlog"]},
        )

    def test_atlas_flags_semantic_models_without_retained_technical_source(self) -> None:
        project = self.service.create_project("Legacy Bim")
        self.service.add_concept(project.id, "DimDate", tags=["table", "bim"])

        package = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")

        self.assertIn(
            "missing-technical-source-evidence",
            {gap["gap_id"] for gap in package["gap_backlog"]},
        )

    def test_nexo_requires_reviewed_candidates_before_emitting_immutable_release(self) -> None:
        project = self.service.create_project("Nexo Flow")
        self.service.upload_context_document(
            project.id,
            "glossary.md",
            b"Cliente Activo: Cliente con compra en los ultimos 12 meses.\nKPI Ventas Netas: ventas menos descuentos.",
            "functional_docs",
            "text/markdown",
        )
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            self.service.scan_business_context(project.id)
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Sales", "Product")
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))

        self.assertGreater(draft["manifest"]["candidate_summary"]["total"], 0)
        with self.assertRaisesRegex(ValueError, "pending_review"):
            self.service.publish_nexo_release(project.id, str(draft["manifest"]["draft_id"]), "Release owner", "too early")

        for candidate in draft["candidates"]:
            self.service.update_nexo_candidate(
                project.id,
                str(draft["manifest"]["draft_id"]),
                str(candidate["candidate_id"]),
                "approved",
                "Business steward",
                "Owner",
                "Validated for pilot",
            )
        release = self.service.publish_nexo_release(
            project.id, str(draft["manifest"]["draft_id"]), "Release owner", "pilot release"
        )

        release_path = Path(str(release["package_path"]))
        self.assertTrue((release_path / "canonical_ontology.json").exists())
        self.assertTrue((release_path / "agent_context_pack.json").exists())
        self.assertEqual(release["manifest"]["approved_candidates"], len(draft["candidates"]))

    def test_llm_settings_can_reference_an_explicit_shared_provider_config(self) -> None:
        shared_env = Path(self.temp_dir.name) / "shared-llm.env"
        shared_env.write_text(
            "LLM_PROVIDER=openai\nLLM_MODEL=gpt-5.6-luna\nLLM_API_KEY=test-key\n",
            encoding="utf-8",
        )

        with patch.dict(os.environ, {"ONTO_LLM_CONFIG_PATH": str(shared_env)}, clear=False):
            settings = load_llm_settings()

        self.assertEqual(settings.provider, "openai")
        self.assertEqual(settings.model, "gpt-5.6-luna")
        self.assertTrue(settings.api_key_present)
        self.assertEqual(settings.configuration_source, "shared_config")
        self.assertEqual(settings.reasoning_effort, "none")

    def test_llm_data_policy_blocks_external_provider_in_local_only_mode(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ONTO_LLM_PROVIDER": "openai",
                "ONTO_LLM_MODEL": "test-model",
                "ONTO_LLM_API_KEY": "test-key",
                "ONTO_LLM_DATA_POLICY": "local_only",
            },
            clear=False,
        ):
            settings = load_llm_settings()

        self.assertEqual(settings.data_policy, "local_only")
        self.assertFalse(settings.enabled)

    def test_llm_data_policy_rejects_unknown_value(self) -> None:
        with patch.dict(os.environ, {"ONTO_LLM_DATA_POLICY": "unrestricted"}, clear=False):
            with self.assertRaisesRegex(ValueError, "approved_external o local_only"):
                load_llm_settings()

    def test_nexo_deterministic_consolidation_keeps_candidates_unchanged(self) -> None:
        project = self.service.create_project("Consolidation")
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))
        draft_path = Path(str(draft["draft_path"])) / "working" / "candidates.json"
        candidates = json.loads(draft_path.read_text(encoding="utf-8"))
        candidates = [
            {
                "candidate_id": "candidate-concept-0001",
                "candidate_type": "concept",
                "name": "Cliente Activo",
                "definition": "Cliente vigente",
                "status": "pending_review",
                "confidence": 0.8,
                "evidence": {},
            },
            {
                "candidate_id": "candidate-concept-0002",
                "candidate_type": "concept",
                "name": "cliente activo",
                "definition": "Cliente con actividad",
                "status": "pending_review",
                "confidence": 0.7,
                "evidence": {},
            },
        ]
        draft_path.write_text(json.dumps(candidates), encoding="utf-8")

        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            package = self.service.generate_nexo_consolidation_suggestions(
                project.id, str(draft["manifest"]["draft_id"])
            )
        suggestion = package["suggestions"][0]
        self.service.update_nexo_consolidation_suggestion(
            project.id, str(draft["manifest"]["draft_id"]), str(suggestion["suggestion_id"]),
            "accepted_as_review_plan", "Data steward", "Review together",
        )
        stored_candidates = json.loads(draft_path.read_text(encoding="utf-8"))

        self.assertEqual(package["mode"], "deterministic")
        self.assertEqual(suggestion["canonical_candidate_id"], "candidate-concept-0001")
        self.assertEqual(stored_candidates[1]["status"], "pending_review")

    def test_nexo_bulk_review_and_applied_consolidation_do_not_approve_canonical(self) -> None:
        project = self.service.create_project("Applied Consolidation")
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))
        draft_id = str(draft["manifest"]["draft_id"])
        draft_path = Path(str(draft["draft_path"])) / "working" / "candidates.json"
        candidates = [
            {"candidate_id": "candidate-concept-0001", "candidate_type": "concept", "name": "Cliente", "definition": "Entidad", "status": "pending_review", "confidence": 0.8, "evidence": {}},
            {"candidate_id": "candidate-concept-0002", "candidate_type": "concept", "name": "cliente", "definition": "Entidad duplicada", "status": "pending_review", "confidence": 0.7, "evidence": {}},
            {"candidate_id": "candidate-kpi-0003", "candidate_type": "kpi", "name": "Ventas", "definition": "Indicador", "status": "pending_review", "confidence": 0.7, "evidence": {}},
        ]
        draft_path.write_text(json.dumps(candidates), encoding="utf-8")
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            package = self.service.generate_nexo_consolidation_suggestions(project.id, draft_id)
        suggestion_id = str(package["suggestions"][0]["suggestion_id"])
        self.service.update_nexo_consolidation_suggestion(
            project.id, draft_id, suggestion_id, "accepted_as_review_plan", "Steward", "Approved plan"
        )
        result = self.service.apply_nexo_consolidation_suggestion(
            project.id, draft_id, suggestion_id, "Steward", "Same concept"
        )
        self.service.bulk_update_nexo_candidates(
            project.id, draft_id, ["candidate-kpi-0003"], "approved", "Steward", "Owner", "Reviewed"
        )
        stored = {item["candidate_id"]: item for item in self.service.get_nexo_draft(project.id, draft_id)["candidates"]}

        self.assertEqual(result["rejected_duplicates"], 1)
        self.assertEqual(stored["candidate-concept-0001"]["status"], "pending_review")
        self.assertEqual(stored["candidate-concept-0002"]["status"], "rejected")
        self.assertEqual(stored["candidate-kpi-0003"]["status"], "approved")

    def test_argos_answers_only_from_a_nexo_release_and_abstains_without_match(self) -> None:
        project = self.service.create_project("Argos")
        self.service.upload_context_document(project.id, "doc.md", b"Cliente Activo: Cliente con compra vigente.", "functional_docs", "text/markdown")
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            self.service.scan_business_context(project.id)
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))
        self.service.bulk_update_nexo_candidates(project.id, str(draft["manifest"]["draft_id"]), [item["candidate_id"] for item in draft["candidates"]], "approved", "Reviewer", "Owner", "Test")
        release = self.service.publish_nexo_release(project.id, str(draft["manifest"]["draft_id"]), "Owner", "Test")
        context_pack_path = Path(str(release["package_path"])) / "agent_context_pack.json"
        context_pack = json.loads(context_pack_path.read_text(encoding="utf-8"))
        context_pack["data_bindings"] = [{"name": "gold_sic.fact_riesgo -> gold_sic.fact_riesgo"}]
        context_pack_path.write_text(json.dumps(context_pack), encoding="utf-8")
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            with patch("ontology_workbench.service.execute_fabric_read_only_query") as execute_query:
                execute_query.return_value = {
                    "status": "connected_read_only_query",
                    "query_name": "risk_summary",
                    "operation": "SELECT",
                    "rows": [{"total_rows": 3, "distinct_sic": 2, "latest_calculation": "2026-08-05"}],
                }
                live_answer = self.service.investigate_release(
                    project.id, str(release["manifest"]["release_id"]), "Cuantos riesgos hay?"
                )
                abstention = self.service.investigate_release(
                    project.id, str(release["manifest"]["release_id"]), "Que planeta es mas grande?"
                )
                sql_abstention = self.service.investigate_release(
                    project.id,
                    str(release["manifest"]["release_id"]),
                    "Ejecuta DELETE FROM clientes",
                )
        execute_query.assert_called_once_with("risk_summary")
        self.assertEqual(live_answer["manifest"]["mode"], "deterministic-context-pack-plus-fabric-read-only")
        self.assertIn("3 registros de riesgo", live_answer["answer"])
        self.assertEqual(
            live_answer["reasoning_advisory"]["level"],
            "standard_reasoning_sufficient",
        )
        self.assertTrue(
            Path(live_answer["package_path"], "traceability.json").exists()
        )
        context_pack["data_bindings"] = []
        context_pack_path.write_text(json.dumps(context_pack), encoding="utf-8")
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            blocked = self.service.investigate_release(
                project.id, str(release["manifest"]["release_id"]), "Cuantos riesgos hay?"
            )
        self.assertNotIn("live_query", blocked)
        self.assertEqual(blocked["manifest"]["mode"], "deterministic-context-pack")
        self.assertEqual(live_answer["manifest"]["status"], "answered")
        self.assertEqual(abstention["manifest"]["status"], "abstained")
        self.assertEqual(sql_abstention["manifest"]["status"], "abstained")
        self.assertNotIn("live_query", sql_abstention)
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            evaluation_cases = self.service.suggest_argos_evaluation_cases(
                project.id, str(release["manifest"]["release_id"])
            )
            evaluation = self.service.evaluate_argos_release(
                project.id, str(release["manifest"]["release_id"]), evaluation_cases
            )
        self.assertEqual(evaluation["summary"]["failed"], 0)
        self.assertTrue(Path(str(evaluation["package_path"])).exists())
        context_pack = release["agent_context_pack"]
        self.assertEqual(context_pack["query_contract"]["allowed_operations"], ["SELECT"])
        with self.assertRaisesRegex(ValueError, "operaciones mutantes"):
            investigate_context_pack(
                {**context_pack, "query_contract": {"allowed_operations": ["SELECT"], "requires_approved_data_binding": True, "disallowed_operations": []}},
                "Que es Cliente Activo?",
                "invalid-contract",
            )

    def test_argos_ignores_generic_comparison_words_when_no_evidence_matches(self) -> None:
        context_pack = {
            "release_id": "release-test",
            "query_contract": {
                "allowed_operations": ["SELECT"],
                "requires_approved_data_binding": True,
                "disallowed_operations": ["INSERT", "UPDATE", "DELETE", "DDL"],
            },
            "usage_boundary": "Solo usar la evidencia aprobada.",
            "concepts": [{"id": "concept-1", "name": "Riesgo", "definition": "Nivel calculado."}],
        }

        investigation = investigate_context_pack(
            context_pack, "Que planeta es mas grande?", "investigation-test"
        )

        self.assertEqual(investigation["manifest"]["status"], "abstained")

    def test_argos_llm_preserves_retrieval_and_abstains_without_context_evidence(self) -> None:
        context_pack = {
            "release_id": "release-llm-test",
            "query_contract": {
                "allowed_operations": ["SELECT"],
                "requires_approved_data_binding": True,
                "disallowed_operations": ["INSERT", "UPDATE", "DELETE", "DDL"],
            },
            "usage_boundary": "Solo usar la evidencia aprobada.",
            "concepts": [{"id": "concept-1", "name": "Riesgo", "definition": "Nivel calculado."}],
        }
        settings = SimpleNamespace(enabled=True, provider="test", model="test")
        plans = [
            {"query_name": None, "parameters": {}, "needs_stronger_model": False, "reasoning_note": ""},
            {"answer": "Riesgo es un nivel calculado.", "interpretation": "", "suggested_questions": [], "visualization": None, "needs_stronger_model": False, "reasoning_note": ""},
        ]
        with patch("ontology_workbench.runtime.call_llm_json", side_effect=plans):
            answered = investigate_context_pack_with_llm(
                context_pack, "Que es Riesgo?", "investigation-1", settings, {}, lambda name, parameters: {},
            )
        self.assertEqual(answered["manifest"]["status"], "answered")
        self.assertEqual([item["name"] for item in answered["retrieval"]], ["Riesgo"])

        with patch(
            "ontology_workbench.runtime.call_llm_json",
            side_effect=[
                {"query_name": None, "parameters": {}, "needs_stronger_model": False, "reasoning_note": ""},
                {"answer": "El planeta Júpiter es el más grande.", "interpretation": "", "suggested_questions": [], "visualization": None, "needs_stronger_model": False, "reasoning_note": ""},
            ],
        ):
            abstained = investigate_context_pack_with_llm(
                context_pack, "Que planeta es mas grande?", "investigation-2", settings, {}, lambda name, parameters: {},
            )
        self.assertEqual(abstained["manifest"]["status"], "abstained")
        self.assertIn("Me abstengo", abstained["answer"])

    def test_argos_routes_only_unambiguous_fabric_data_questions(self) -> None:
        self.assertEqual(select_fabric_query("Cuantos riesgos hay?"), "risk_summary")
        self.assertEqual(select_fabric_query("Dame los riesgos del SIC 12"), "risk_sic")
        self.assertEqual(select_fabric_query("Cuales son los niveles de riesgo?"), "risk_levels")
        self.assertEqual(select_fabric_query("Cuantos valores REAL y DEFAULT hay?"), "impact_statuses")
        question = "Cual es el riesgo de la regla 1003 en el SIC12?"
        self.assertEqual(select_fabric_query(question), "risk_rule_sic")
        self.assertEqual(fabric_query_parameters(question), (1003, 12))
        self.assertEqual(
            select_fabric_query("Cual es el valor de la regla 1003 en el SIC 12?"),
            "risk_rule_sic",
        )
        self.assertEqual(
            fabric_query_parameters("Cual es el valor del riesgo 1 en el 12?"),
            (1, 12),
        )
        self.assertEqual(select_fabric_query("Como se calcula el riesgo?"), None)

    def test_argos_routes_a_configured_commercial_query_catalog(self) -> None:
        catalog = normalize_query_catalog(
            [
                {
                    "query_name": "sales_by_customer",
                    "description": "Ventas de un cliente.",
                    "adapter": "local_synthetic",
                    "template_id": "sales_by_customer",
                    "binding_required": "FactSales",
                    "allowed_parameters": ["customer_id"],
                    "max_rows": 100,
                    "routing": {"all_terms": ["ventas", "cliente"]},
                    "parameter_extractors": {
                        "customer_id": {
                            "type": "integer",
                            "patterns": [r"\bcliente\s*(\d+)\b"],
                        }
                    },
                }
            ]
        )

        question = "Cuantas ventas tiene el cliente 42?"
        query_name = select_catalog_query(question, catalog)
        parameters = extract_query_parameters(question, catalog[query_name])

        self.assertEqual(query_name, "sales_by_customer")
        self.assertEqual(ordered_query_parameters(catalog[query_name], parameters), (42,))

    def test_argos_executes_a_configured_local_synthetic_query(self) -> None:
        catalog = normalize_query_catalog(
            [
                {
                    "query_name": "sales_by_customer",
                    "adapter": "local_synthetic",
                    "template_id": "sales_by_customer",
                    "binding_required": "FactSales",
                    "allowed_parameters": ["customer_id"],
                    "max_rows": 10,
                }
            ]
        )
        context_pack = {
            "query_catalog": catalog,
            "technical_assets": [{"name": "FactSales"}],
            "data_bindings": [],
        }

        result = self.service._execute_catalog_query(context_pack, "sales_by_customer", (42,))

        self.assertEqual(result["status"], "local_synthetic_query")
        self.assertEqual(result["rows"][0]["customer_name"], "Acme Sur")

    def test_mariadb_schema_parser_reads_ddl_without_rows(self) -> None:
        with TemporaryDirectory() as temp_dir:
            dump_path = Path(temp_dir) / "schema.sql"
            dump_path.write_text(
                "CREATE TABLE IF NOT EXISTS `clientes` (\n"
                "  `id` int(11) NOT NULL,\n"
                "  `nombre` varchar(100) DEFAULT NULL,\n"
                "  PRIMARY KEY (`id`)\n"
                ") ENGINE=InnoDB;\n"
                "CREATE TABLE IF NOT EXISTS `pedidos` (\n"
                "  `id` int(11) NOT NULL,\n"
                "  `cliente` int(11) NOT NULL,\n"
                "  CONSTRAINT `fk_pedido_cliente` FOREIGN KEY (`cliente`) REFERENCES `clientes` (`id`)\n"
                ") ENGINE=InnoDB;\n"
                "INSERT INTO `clientes` VALUES (1,'No debe importarse');\n",
                encoding="utf-8",
            )

            parsed = parse_mariadb_schema_dump(dump_path)

        self.assertEqual(parsed["table_count"], 2)
        self.assertEqual(parsed["column_count"], 4)
        self.assertEqual(parsed["relationship_count"], 1)
        self.assertEqual(parsed["model"]["tables"][0]["name"], "clientes")

    def test_argos_routes_nalub_mariadb_catalog(self) -> None:
        catalog = normalize_query_catalog(
            [
                {
                    "query_name": "customer_debt",
                    "adapter": "mariadb",
                    "template_id": "customer_debt",
                    "binding_required": "clientes",
                    "connection_profile": "nalub-test",
                    "allowed_parameters": ["customer_id"],
                    "routing": {"all_terms": ["deuda", "cliente"]},
                    "parameter_extractors": {
                        "customer_id": {
                            "type": "integer",
                            "patterns": [r"\bcliente\s*(\d+)\b"],
                        }
                    },
                }
            ]
        )

        question = "Cuanta deuda tiene el cliente 12?"
        self.assertEqual(select_catalog_query(question, catalog), "customer_debt")
        parameters = extract_query_parameters(question, catalog["customer_debt"])
        self.assertEqual(ordered_query_parameters(catalog["customer_debt"], parameters), (12,))

    def test_argos_routes_nalub_sales_catalog(self) -> None:
        catalog = normalize_query_catalog(
            [
                {
                    "query_name": "sales_summary",
                    "adapter": "mariadb",
                    "template_id": "sales_summary",
                    "binding_required": "pedidos",
                    "connection_profile": "nalub-test",
                    "allowed_parameters": [],
                    "max_rows": 24,
                    "routing": {"any_terms": ["venta", "ventas"]},
                }
            ]
        )

        self.assertEqual(
            select_catalog_query("Calculame las ventas y su evolucion por mes", catalog),
            "sales_summary",
        )
        self.assertIn("DATE_FORMAT(fecha", MARIADB_QUERY_TEMPLATES["sales_summary"])
        self.assertIn("importeTotal", MARIADB_QUERY_TEMPLATES["sales_summary"])

    def test_argos_routes_product_demand_by_year(self) -> None:
        catalog = normalize_query_catalog(
            [
                {
                    "query_name": "product_demand_by_year",
                    "adapter": "mariadb",
                    "template_id": "product_demand_by_year",
                    "binding_required": "pedidoItems",
                    "connection_profile": "nalub-test",
                    "allowed_parameters": ["year"],
                    "max_rows": 10,
                    "routing": {
                        "all_terms": ["productos"],
                        "any_terms": ["demandados", "unidades", "pedidos"],
                        "requires_parameter": "year",
                    },
                    "parameter_extractors": {
                        "year": {
                            "type": "integer",
                            "patterns": [r"\b(20\d{2})\b"],
                        }
                    },
                }
            ]
        )
        question = "Quiero los 10 productos mas demandados de 2025, con unidades y pedidos"
        self.assertEqual(select_catalog_query(question, catalog), "product_demand_by_year")
        parameters = extract_query_parameters(question, catalog["product_demand_by_year"])
        self.assertEqual(ordered_query_parameters(catalog["product_demand_by_year"], parameters), (2025,))
        self.assertIn("pedidoItems", MARIADB_QUERY_TEMPLATES["product_demand_by_year"])
        self.assertIn("unidades_solicitadas", MARIADB_QUERY_TEMPLATES["product_demand_by_year"])

    def test_empty_project_catalog_does_not_fall_back_to_fabric(self) -> None:
        self.assertEqual(catalog_for_context({"query_catalog": []}), {})

    def test_connection_profiles_are_isolated_per_project(self) -> None:
        first_project = self.service.create_project("Nalub")
        second_project = self.service.create_project("Human Resources")

        profile = self.service.save_mariadb_connection_profile(
            first_project.id,
            "nalub-test",
            "db.test.local",
            3306,
            "nalub_reader",
            "test-secret",
            "nalub",
        )

        self.assertEqual(profile["profile_id"], "nalub-test")
        self.assertEqual(
            [item["profile_id"] for item in self.service.list_connection_profiles(first_project.id)],
            ["nalub-test"],
        )
        self.assertEqual(self.service.list_connection_profiles(second_project.id), [])
        project_json = (Path(self.temp_dir.name) / "projects" / f"{first_project.id}.json").read_text()
        self.assertNotIn("test-secret", project_json)

    def test_connection_profiles_reject_unsafe_ids(self) -> None:
        project = self.service.create_project("Nalub")

        with self.assertRaises(ValueError):
            self.service.save_mariadb_connection_profile(
                project.id,
                "../shared",
                "db.test.local",
                3306,
                "reader",
                "secret",
                "nalub",
            )

    def test_mariadb_catalog_requires_connection_profile(self) -> None:
        with self.assertRaises(ValueError):
            normalize_query_catalog(
                [
                    {
                        "query_name": "customer_debt",
                        "adapter": "mariadb",
                        "template_id": "customer_debt",
                    }
                ]
            )

    def test_mariadb_templates_reject_invalid_parameters_before_connecting(self) -> None:
        with self.assertRaisesRegex(ValueError, "customer_id entero"):
            execute_mariadb_read_only_query("customer_debt", ())
        with self.assertRaisesRegex(ValueError, "año entero"):
            execute_mariadb_read_only_query("product_demand_by_year", (1999,))
        with self.assertRaisesRegex(ValueError, "limite entero"):
            execute_mariadb_read_only_query("product_availability", ("50",))

    def test_argos_returns_interpretation_and_mermaid_for_risk_question(self) -> None:
        project = self.service.create_project("Argos Mermaid")
        self.service.upload_context_document(
            project.id, "risk.md", b"Riesgo: nivel calculado.", "functional_docs", "text/markdown"
        )
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            self.service.scan_business_context(project.id)
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))
        self.service.bulk_update_nexo_candidates(
            project.id, str(draft["manifest"]["draft_id"]),
            [item["candidate_id"] for item in draft["candidates"]],
            "approved", "Reviewer", "Owner", "Test",
        )
        release = self.service.publish_nexo_release(
            project.id, str(draft["manifest"]["draft_id"]), "Owner", "Test"
        )
        context_pack_path = Path(str(release["package_path"])) / "agent_context_pack.json"
        context_pack = json.loads(context_pack_path.read_text(encoding="utf-8"))
        context_pack["data_bindings"] = [{"name": "gold_sic.fact_riesgo"}]
        context_pack_path.write_text(json.dumps(context_pack), encoding="utf-8")
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            with patch("ontology_workbench.service.execute_fabric_read_only_query") as execute_query:
                execute_query.return_value = {
                    "status": "connected_read_only_query", "query_name": "risk_rule_sic",
                    "operation": "SELECT", "rows": [{
                        "id_risc": 1, "sic": 12, "riesgo_final_texto": "ALT",
                        "probabilidad_final_texto": "MIG", "impacto_final_texto": "ALT",
                        "metodo_calculo": "MATRIZ_4X4",
                    }],
                }
                result = self.service.investigate_release(
                    project.id, str(release["manifest"]["release_id"]),
                    "Mostrame un diagrama Mermaid de por que el riesgo de la regla 1 en el SIC 12 es alto",
                )
        self.assertIn("MATRIZ_4X4", result["interpretation"])
        self.assertEqual(result["visualization"]["type"], "mermaid")
        self.assertIn("Riesgo final: ALT", result["visualization"]["code"])
        self.assertEqual(result["reasoning_advisory"]["model_used"], "deterministic-runtime")

    def test_nexo_release_includes_reviewed_canonical_model_elements(self) -> None:
        project = self.service.create_project("Canonical model")
        assessment = self.service.create_atlas_assessment(project.id, "Client", "Sales", "Product")
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))
        draft_id = str(draft["manifest"]["draft_id"])
        candidates_path = Path(str(draft["draft_path"])) / "working" / "candidates.json"
        candidates = [
            {
                "candidate_id": "candidate-concept-0001",
                "candidate_type": "concept",
                "name": "Cliente",
                "definition": "Persona u organización que realiza compras.",
                "status": "pending_review",
                "confidence": 1.0,
                "origin": "test",
                "evidence": {"source_document_id": "doc-1", "source_chunk_id": "chunk-1", "source_excerpt": "Cliente", "evidence_status": "available"},
                "decision": None,
            },
            {
                "candidate_id": "candidate-concept-0002",
                "candidate_type": "concept",
                "name": "Pedido",
                "definition": "Solicitud de compra de un cliente.",
                "status": "pending_review",
                "confidence": 1.0,
                "origin": "test",
                "evidence": {"source_document_id": "doc-1", "source_chunk_id": "chunk-2", "source_excerpt": "Pedido", "evidence_status": "available"},
                "decision": None,
            },
        ]
        candidates_path.write_text(json.dumps(candidates), encoding="utf-8")
        candidate_ids = [str(item["candidate_id"]) for item in candidates]
        self.service.bulk_update_nexo_candidates(
            project.id, draft_id, candidate_ids, "approved", "Steward", "Business owner", "Validated"
        )
        property_element = self.service.add_nexo_model_element(
            project.id, draft_id, "property", "estado de cliente",
            "Estado comercial actual del cliente.", "Sales Operations", [candidate_ids[0]],
        )
        relationship_element = self.service.add_nexo_model_element(
            project.id, draft_id, "relationship", "cliente realiza pedido",
            "Relaciona un cliente con sus pedidos.", "Sales Operations", candidate_ids[:2],
        )
        binding_element = self.service.add_nexo_model_element(
            project.id, draft_id, "source_binding", "cliente vinculado a fuente",
            "Binding aprobado para consulta de cliente.", "Sales Operations", candidate_ids[:2],
        )
        with self.assertRaisesRegex(ValueError, "elementos del modelo pendientes"):
            self.service.publish_nexo_release(project.id, draft_id, "Owner", "too early")
        for element in (property_element, relationship_element, binding_element):
            self.service.update_nexo_model_element(
                project.id, draft_id, str(element["element_id"]), "approved",
                "Steward", "Business owner", "Validated for release",
            )
        release = self.service.publish_nexo_release(project.id, draft_id, "Owner", "canonical release")
        canonical = release["canonical_ontology"]
        self.assertEqual(canonical["format"], "nexo-canonical-ontology-v0.2")
        self.assertEqual(len(canonical["properties"]), 1)
        self.assertEqual(len(canonical["relationships"]), 1)
        self.assertEqual(len(canonical["data_bindings"]), 1)
        self.assertEqual(canonical["ownership"][0]["owner"], "Sales Operations")
        self.assertEqual(len(release["agent_context_pack"]["relationships"]), 1)
        self.assertTrue(release["agent_context_pack"]["query_contract"]["requires_approved_data_binding"])
        comparison = self.service.compare_nexo_draft_to_release(
            project.id, draft_id, str(release["manifest"]["release_id"])
        )
        self.assertTrue(Path(str(comparison["comparison_path"])).exists())
        self.assertGreater(comparison["summary"]["unchanged"], 0)
        package = self.service.prepare_interoperability_package(
            project.id, str(release["manifest"]["release_id"]), "fabric", "Architect", "Pilot mapping"
        )
        self.assertEqual(package["manifest"]["status"], "ready_for_review")
        self.assertEqual(package["manifest"]["publication_mode"], "local_mapping_only")
        self.assertTrue(Path(str(package["package_path"])).exists())
        self.assertTrue(package["mapping"]["mappings"])
        mappings = package["mapping"]["mappings"]
        self.assertTrue(all(str(mapping["source_id"]).strip() for mapping in mappings))
        binding_mappings = [mapping for mapping in mappings if mapping["source_type"] == "data_binding"]
        self.assertEqual(len(binding_mappings), 1)
        self.assertEqual(binding_mappings[0]["target_object_kind"], "approved_source_binding")
        export_dir = Path(str(package["package_path"])) / "export"
        self.assertTrue((export_dir / "coverage_report.md").exists())
        self.assertTrue((export_dir / "fabric" / "ontology" / "create_ontology_request.json").exists())
        self.assertTrue((Path(str(package["package_path"])) / "coverage.json").exists())

    def test_semantic_comparison_detects_changed_definition_between_releases(self) -> None:
        baseline = {
            "kind": "release",
            "payload": {
                "manifest": {"release_id": "release-1", "created_at": "2026-08-01T00:00:00+00:00"},
                "canonical_ontology": {
                    "concepts": [{"name": "Cliente", "definition": "Definición inicial."}],
                    "business_rules": [], "kpis": [], "properties": [], "relationships": [], "synonyms": [], "constraints": [],
                },
            },
        }
        candidate = {
            "kind": "release",
            "payload": {
                "manifest": {"release_id": "release-2", "created_at": "2026-08-02T00:00:00+00:00"},
                "canonical_ontology": {
                    "concepts": [{"name": "Cliente", "definition": "Definición actualizada."}],
                    "business_rules": [], "kpis": [], "properties": [], "relationships": [], "synonyms": [], "constraints": [],
                },
            },
        }
        comparison = compare_nexo_artifacts(baseline, candidate)

        self.assertEqual(comparison["summary"]["changed"], 1)
        self.assertEqual(comparison["changed"][0]["changes"], ["definition"])

    def test_upload_context_document_and_scan_inventory_without_llm(self) -> None:
        project = self.service.create_project("Context")
        self.service.add_concept(project.id, "Cliente Activo")
        content = (
            b"Cliente Activo: Cliente con compra en los ultimos 12 meses\n"
            b"KPI Ventas Netas: ventas brutas menos descuentos\n"
            b"El pedido cancelado no debe computarse en revenue\n"
            b"Que definicion oficial usamos para cliente activo?\n"
        )

        document = self.service.upload_context_document(
            project.id,
            filename="glosario.md",
            content=content,
            doc_type="functional_docs",
            content_type="text/markdown",
        )

        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            inventory = self.service.scan_business_context(project.id)

        self.assertEqual(document.extraction_status, "extracted")
        self.assertGreater(document.extracted_chars, 20)
        self.assertEqual(inventory["scan_mode"], "heuristic")
        self.assertGreaterEqual(len(inventory["business_terms"]), 1)
        self.assertGreaterEqual(len(inventory["definitions"]), 1)
        self.assertGreaterEqual(len(inventory["business_rules"]), 1)
        self.assertGreaterEqual(len(inventory["kpis"]), 1)

    def test_document_source_deduplication_keeps_first_path_for_each_content(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.md"
            duplicate = root / "nested" / "duplicate.md"
            unique = root / "unique.md"
            duplicate.parent.mkdir()
            first.write_bytes(b"same document")
            duplicate.write_bytes(b"same document")
            unique.write_bytes(b"other document")

            selected = unique_file_paths_by_content([first, duplicate, unique])

        self.assertEqual(selected, [first, unique])

    def test_upload_context_document_shortens_only_physical_storage_name(self) -> None:
        project = self.service.create_project("Long filenames")
        filename = f"document-{'nested-' * 40}source.md"

        document = self.service.upload_context_document(
            project.id,
            filename,
            b"Cliente Activo: cliente vigente.",
            "business_context",
            "text/markdown",
        )

        self.assertEqual(document.filename, filename)
        self.assertTrue(Path(document.stored_path).exists())
        self.assertLessEqual(len(Path(document.stored_path).name), 130)

    def test_context_scanner_reads_markdown_glossary_and_rule_tables(self) -> None:
        project = self.service.create_project("Markdown Context")
        content = (
            b"| Dato / metadata | Que significa funcionalmente |\n"
            b"| --- | --- |\n"
            b"| `pct_edr` | porcentaje de equipos con EDR operativo |\n\n"
            b"| gold_sic.fact_riesgo | salida final por SIC y por bloque |\n\n"
            b"| Codigo | Nombre | Metrica | Umbral |\n"
            b"| --- | --- | --- | --- |\n"
            b"| 1003 | Parches desactualizados | porcentaje de equipos sin actualizar | >= 90 = alto |\n"
        )
        self.service.upload_context_document(
            project.id, "risk.md", content, "functional_docs", "text/markdown"
        )

        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            inventory = self.service.scan_business_context(project.id)

        definitions = {item["term"]: item["definition"] for item in inventory["definitions"]}
        self.assertEqual(definitions["pct_edr"], "porcentaje de equipos con EDR operativo")
        self.assertEqual(definitions["gold_sic.fact_riesgo"], "salida final por SIC y por bloque")
        self.assertTrue(any(item["text"].startswith("Regla 1003") for item in inventory["business_rules"]))
        self.assertTrue(any(item["text"].startswith("Regla 1003") for item in inventory["kpis"]))

    def test_document_uploads_receive_unique_ids_within_the_same_second(self) -> None:
        project = self.service.create_project("Unique Documents")

        first = self.service.upload_context_document(
            project.id, "first.md", b"Primer documento", "functional_docs", "text/markdown"
        )
        second = self.service.upload_context_document(
            project.id, "second.md", b"Segundo documento", "functional_docs", "text/markdown"
        )

        self.assertNotEqual(first.document_id, second.document_id)
        self.assertNotEqual(first.extracted_text_path, second.extracted_text_path)
        self.assertEqual(len(self.service.list_context_documents(project.id)), 2)

    def test_atlas_assessment_writes_reproducible_local_package(self) -> None:
        project = self.service.create_project("Sales Assessment")
        project = self.service.update_metadata(project.id, {"owner": "sales-steward"})
        project = self.service.add_concept(
            project.id, "DimCustomer", definition="Customer dimension", tags=["table", "bim"]
        )
        project = self.service.add_concept(
            project.id,
            "DimCustomer[CustomerKey]",
            definition="Customer key",
            tags=["column", "bim"],
        )
        self.service.upload_context_document(
            project.id,
            "sales-glossary.md",
            b"Cliente Activo: Cliente con compra en los ultimos 12 meses\n",
            "functional_docs",
            "text/markdown",
        )
        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            self.service.scan_business_context(project.id)

        package = self.service.create_atlas_assessment(
            project.id,
            client_id="Client A",
            domain_id="Sales",
            data_product_id="Sales Performance",
        )

        package_path = Path(str(package["package_path"]))
        self.assertTrue(package_path.exists())
        self.assertEqual(package["manifest"]["product"], "Atlas")
        self.assertEqual(package["manifest"]["scope"]["client_id"], "client-a")
        self.assertGreater(package["readiness_score"]["overall_score"], 0)
        self.assertTrue((package_path / "manifest.json").exists())
        self.assertTrue((package_path / "semantic_inventory.json").exists())
        self.assertTrue((package_path / "source_inventory.json").exists())
        self.assertTrue((package_path / "evidence_index.json").exists())
        self.assertTrue((package_path / "assessment_review.json").exists())
        self.assertTrue((package_path / "gap_backlog.json").exists())
        self.assertTrue((package_path / "execution_summary.md").exists())
        report = (package_path / "execution_summary.md").read_text(encoding="utf-8")
        self.assertIn("## Lectura ejecutiva", report)
        self.assertIn("sales-glossary.md", report)
        self.assertIn("## Brechas y acciones sugeridas", report)
        self.assertIn("## Limites del diagnostico", report)
        self.assertIn("no certifica que los datos esten listos para agentes", report)
        self.assertEqual(len(self.service.list_atlas_assessments(project.id)), 1)
        evidence_index = json.loads((package_path / "evidence_index.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence_index["summary"]["chunks"], 1)

    def test_atlas_review_records_human_baseline_decision_without_approving_ontology(self) -> None:
        project = self.service.create_project("Reviewed Assessment")
        package = self.service.create_atlas_assessment(project.id, "Client", "Domain", "Product")

        review = self.service.update_atlas_review(
            project.id,
            str(package["manifest"]["run_id"]),
            "needs_follow_up",
            "Ana Steward",
            "Business steward",
            "Asignar owner antes de continuar.",
        )
        listed = self.service.list_atlas_assessments(project.id)

        self.assertEqual(review["status"], "needs_follow_up")
        self.assertEqual(review["scope"], "assessment_baseline_only")
        self.assertEqual(listed[0]["assessment_review"]["reviewer"], "Ana Steward")

    def test_atlas_marks_legacy_duplicate_document_identifiers_as_a_gap(self) -> None:
        project = self.service.create_project("Legacy Source Integrity")
        first = self.service.upload_context_document(
            project.id, "first.md", b"Primero", "functional_docs", "text/markdown"
        )
        second = self.service.upload_context_document(
            project.id, "second.md", b"Segundo", "functional_docs", "text/markdown"
        )
        documents = self.service.list_context_documents(project.id)
        documents[1].document_id = first.document_id
        self.store.save_documents_manifest(project.id, documents)

        package = self.service.create_atlas_assessment(
            project.id, "Client", "Domain", "Product"
        )

        gap_ids = {gap["gap_id"] for gap in package["gap_backlog"]}
        self.assertIn("duplicate-document-identifiers", gap_ids)
        sources = package["source_inventory"]["sources"]
        self.assertNotEqual(sources[0]["content_sha256"], sources[1]["content_sha256"])

    def test_repair_context_document_ids_reextracts_sources_and_invalidates_context(self) -> None:
        project = self.service.create_project("Repair Context")
        first = self.service.upload_context_document(
            project.id, "first.md", b"Primera fuente", "functional_docs", "text/markdown"
        )
        self.service.upload_context_document(
            project.id, "second.md", b"Segunda fuente", "functional_docs", "text/markdown"
        )
        documents = self.service.list_context_documents(project.id)
        documents[1].document_id = first.document_id
        self.store.save_documents_manifest(project.id, documents)
        self.store.save_business_context_inventory(project.id, {"definitions": [{"term": "stale"}]})

        summary = self.service.repair_context_document_ids(project.id)
        repaired_documents = self.service.list_context_documents(project.id)
        inventory = self.service.get_business_context_inventory(project.id)

        self.assertEqual(summary, {"repaired": 2, "missing_sources": 0})
        self.assertTrue(self.service.get_context_document_integrity(project.id)["is_valid"])
        self.assertEqual(len({document.document_id for document in repaired_documents}), 2)
        self.assertEqual(
            [self.store.load_document_text(project.id, document.document_id) for document in repaired_documents],
            ["Primera fuente", "Segunda fuente"],
        )
        self.assertEqual(inventory["status"], "invalidated")

    def test_context_scanner_chunks_long_documents_and_keeps_heuristic_evidence(self) -> None:
        project = self.service.create_project("Chunked Context")
        content = ("Cliente Activo: Cliente con compra vigente.\n" + "texto de contexto " * 900).encode()
        document = self.service.upload_context_document(
            project.id, "long.md", content, "functional_docs", "text/markdown"
        )
        chunks = build_document_chunks(
            [document], {document.document_id: self.store.load_document_text(project.id, document.document_id)}
        )

        with patch.dict(os.environ, {"ONTO_LLM_PROVIDER": "disabled"}, clear=False):
            inventory = self.service.scan_business_context(project.id)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(str(chunk["text"])) <= CONTEXT_CHUNK_SIZE for chunk in chunks))
        self.assertEqual(inventory["chunking"]["chunks"], len(chunks))
        self.assertTrue(inventory["definitions"][0]["source_chunk_id"].endswith("chunk-001"))
        self.assertTrue(inventory["definitions"][0]["source_excerpt"])
        chunks_path = Path(self.temp_dir.name) / "context" / project.id / "working" / "chunks" / "chunks.json"
        self.assertTrue(chunks_path.exists())


class AtlasMultiSourceTests(unittest.TestCase):
    ERP_DDL = (
        "CREATE TABLE `clientes` (\n  `id_cliente` int(11) NOT NULL,\n  `razon_social` varchar(200),\n"
        "  PRIMARY KEY (`id_cliente`),\n  KEY `idx` (`razon_social`)\n) ENGINE=InnoDB;\n"
        "CREATE TABLE `pedidos` (\n  `id_pedido` int NOT NULL,\n  `id_cliente` int NOT NULL,\n"
        "  `total` decimal(14,2),\n"
        "  CONSTRAINT `fk` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id_cliente`)\n) ENGINE=InnoDB;\n"
    ).encode("utf-8")
    LAKEHOUSE_CSV = (
        "table_catalog,table_schema,table_name,column_name,data_type\n"
        "main,gold,dim_cliente,cliente_id,BIGINT\n"
        "main,gold,dim_cliente,nombre,STRING\n"
        "main,gold,fact_ventas,cliente_id,BIGINT\n"
        "main,gold,fact_ventas,importe,\"DECIMAL(14,2)\"\n"
    ).encode("utf-8")

    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.store = ProjectStore(Path(self.temp_dir.name) / "projects")
        self.service = WorkbenchService(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generic_ddl_parser_reads_bracketed_and_inline_references(self) -> None:
        parsed = parse_sql_ddl(
            "CREATE TABLE [dbo].[Accounts] ([AccountId] INT NOT NULL PRIMARY KEY, [CheckinDate] DATE);\n"
            "CREATE OR REPLACE TABLE main.gold.opps (id BIGINT, account_id INT REFERENCES [dbo].[Accounts]([AccountId]),"
            " tags ARRAY<STRING>, amount DECIMAL(10,2), CONSTRAINT pk PRIMARY KEY (id)) USING DELTA;"
        )

        tables = {table["name"]: table for table in parsed["model"]["tables"]}
        self.assertEqual(set(tables), {"dbo.Accounts", "main.gold.opps"})
        self.assertEqual([c["name"] for c in tables["dbo.Accounts"]["columns"]], ["AccountId", "CheckinDate"])
        self.assertEqual(len(tables["main.gold.opps"]["columns"]), 4)
        self.assertEqual(parsed["model"]["relationships"][0]["toTable"], "dbo.Accounts")

    def test_columns_csv_requires_table_and_column_headers(self) -> None:
        parsed = parse_columns_csv(self.LAKEHOUSE_CSV.decode("utf-8"))
        self.assertEqual(parsed["table_count"], 2)
        self.assertEqual(parsed["column_count"], 4)
        with self.assertRaisesRegex(ValueError, "table_name"):
            parse_columns_csv("a,b\n1,2\n")

    def test_assessment_inventories_several_systems_and_maps_shared_entities(self) -> None:
        project = self.service.create_project("Distribuido")
        erp = self.service.register_data_source(project.id, "ERP", "mariadb", owner="Sistemas")
        lake = self.service.register_data_source(project.id, "Lakehouse", "databricks")
        budget = self.service.register_data_source(project.id, "Presupuesto", "files", owner="Control")
        self.service.import_source_metadata_file(project.id, erp.source_id, "erp.sql", self.ERP_DDL)
        self.service.import_source_metadata_file(project.id, lake.source_id, "cols.csv", self.LAKEHOUSE_CSV)
        self.service.add_use_case(
            project.id, "Margen por cliente", "Que clientes dejan mas margen?", "Comercial", "alta",
            [erp.source_id, lake.source_id],
        )

        package = self.service.create_atlas_assessment(project.id, "Client", "Sales", "Product")

        technical = package["source_inventory"]["technical_sources"]
        self.assertEqual({item["source_id"] for item in technical}, {erp.source_id, lake.source_id})
        self.assertEqual(package["source_inventory"]["declared_sources"][0]["source_id"], budget.source_id)
        shared = {row["entity"]: row for row in package["cross_source_map"]["shared_entities"]}
        self.assertEqual(shared["cliente"]["common_key"], "cliente#id")
        dimensions = {item["dimension"] for item in package["readiness_score"]["dimensions"]}
        self.assertIn("cross_source_alignment", dimensions)
        gaps = {gap["gap_id"]: gap for gap in package["gap_backlog"]}
        self.assertIn(f"source-not-inventoried:{budget.source_id}", gaps)
        self.assertEqual(gaps[f"source-without-owner:{lake.source_id}"]["use_case_ids"], ["margen-por-cliente"])
        self.assertNotIn("missing-use-cases", gaps)
        self.assertNotEqual(package["readiness_score"]["interpretation"], "strong_foundation")
        details = self.service.get_atlas_assessment(project.id, str(package["manifest"]["run_id"]))
        self.assertEqual(details["scope_definition"]["use_cases"][0]["name"], "Margen por cliente")
        self.assertIn("## Mapa entre sistemas", details["execution_summary"])

    def test_reimporting_a_source_replaces_only_its_objects(self) -> None:
        project = self.service.create_project("Reimport")
        erp = self.service.register_data_source(project.id, "ERP", "mariadb")
        lake = self.service.register_data_source(project.id, "Lakehouse", "databricks")
        self.service.import_source_metadata_file(project.id, erp.source_id, "erp.sql", self.ERP_DDL)
        self.service.import_source_metadata_file(project.id, lake.source_id, "cols.csv", self.LAKEHOUSE_CSV)
        before = len(self.service.get_project(project.id).concepts)

        self.service.import_source_metadata_file(project.id, erp.source_id, "erp.sql", self.ERP_DDL)
        project_after = self.service.get_project(project.id)

        self.assertEqual(len(project_after.concepts), before)
        self.assertFalse(
            [issue for issue in self.service.validate_project(project.id) if issue.code == "duplicate-concept-name"]
        )
        self.service.delete_data_source(project.id, lake.source_id)
        remaining = self.service.get_project(project.id)
        self.assertEqual({c.metadata.get("source.id") for c in remaining.concepts}, {erp.source_id})
        self.assertEqual([source.source_id for source in remaining.sources], [erp.source_id])

    def test_legacy_imports_register_a_source_automatically(self) -> None:
        project = self.service.create_project("Legacy import")
        content = json.dumps({"model": {"tables": [{"name": "DimDate", "columns": [{"name": "Date"}]}]}}).encode()

        imported, _ = self.service.import_bim_file(project.id, "ventas.bim", content)

        self.assertEqual(imported.sources[0].platform, "powerbi")
        self.assertEqual(imported.sources[0].status, "inventoried")
        self.assertTrue(all(c.metadata.get("source.id") == imported.sources[0].source_id for c in imported.concepts))


class ArgosPresentationTests(unittest.TestCase):
    def test_starter_questions_prefer_catalog_examples_and_fall_back_to_known_queries(self) -> None:
        catalog = {
            "custom": {"example_question": "¿Cuánto vendimos ayer?"},
            "risk_levels": {},
            "unknown": {"description": "Sin ejemplo"},
        }
        self.assertEqual(
            starter_questions(catalog),
            ["¿Cuánto vendimos ayer?", "¿Cómo se distribuyen los riesgos por nivel?"],
        )

    def test_infer_visualization_uses_catalog_spec_then_row_shape(self) -> None:
        rows = [{"nivel": "Alto", "total": 3, "extra": "x"}, {"nivel": "Bajo", "total": 5, "extra": "y"}]
        self.assertEqual(infer_visualization(rows), {"type": "bar", "x": "nivel", "y": "total"})
        self.assertEqual(
            infer_visualization(rows, {"visualization": {"type": "bar", "x": "extra", "y": "total"}}),
            {"type": "bar", "x": "extra", "y": "total"},
        )
        self.assertEqual(
            infer_visualization([{"a": 1, "b": "x"}], {"visualization": {"type": "metrics", "fields": ["b", "missing"]}}),
            {"type": "metrics", "fields": ["b"]},
        )
        self.assertEqual(infer_visualization([{"a": 1, "b": 2}]), {"type": "metrics", "fields": ["a", "b"]})
        self.assertIsNone(infer_visualization([{"texto": "a"}, {"texto": "b"}]))
        self.assertIsNone(infer_visualization([]))

    def test_legacy_risk_catalog_declares_examples_and_visualizations(self) -> None:
        catalog = normalize_query_catalog(LEGACY_FABRIC_QUERY_CATALOG)
        self.assertEqual(catalog["risk_levels"]["visualization"]["type"], "bar")
        self.assertIn("SIC 12", catalog["risk_rule_sic"]["example_question"])

    def test_parse_evaluation_cases_validates_expected_status(self) -> None:
        cases, invalid = parse_evaluation_cases(
            "¿Qué es Cliente activo? | answered | Cliente activo\n"
            "\n"
            "Solo pregunta\n"
            "¿Planeta? | abstained |\n"
            "Mal | quizas\n"
            " | answered\n"
        )
        self.assertEqual([case["expected_status"] for case in cases], ["answered", "answered", "abstained"])
        self.assertEqual(cases[0]["expected_item_name"], "Cliente activo")
        self.assertEqual(invalid, ["5", "6"])


class PlatformExportTests(unittest.TestCase):
    def _release(self, lake_platform: str = "databricks") -> dict[str, object]:
        def candidate(candidate_id: str, name: str, definition: str, metadata: dict[str, str] | None = None) -> dict[str, object]:
            item = {"id": candidate_id, "name": name, "definition": definition, "confidence": 1.0,
                    "source_binding": {"source_document_id": "doc-1", "source_chunk_id": "doc-1-chunk-001"}}
            if metadata:
                item["technical_metadata"] = metadata
            return item

        def element(element_id: str, name: str, linked: list[str]) -> dict[str, object]:
            return {"id": element_id, "name": name, "definition": f"Definicion de {name}", "owner": "Negocio",
                    "linked_candidate_ids": linked}

        return {
            "manifest": {"release_id": "release-test", "project_id": "p", "source_assessment": {"scope": {"domain_id": "comercial"}}},
            "canonical_ontology": {
                "concepts": [candidate("c1", "Cliente activo", "Cliente con compra en 12 meses."),
                             candidate("c2", "Pedido", "Solicitud de compra.")],
                "kpis": [candidate("k1", "Ventas netas", "Importe facturado menos descuentos.")],
                "business_rules": [candidate("r1", "Anulados", "Un pedido anulado no cuenta como venta.")],
                "technical_assets": [
                    candidate("t1", "gold.dim_cliente", "tabla", {"bim.objectType": "table", "source.platform": lake_platform}),
                    candidate("t2", "clientes", "tabla", {"bim.objectType": "table", "source.platform": "mariadb"}),
                ],
                "properties": [element("p1", "Zona", ["c1"])],
                "relationships": [element("rel1", "realiza", ["c1", "c2"])],
                "synonyms": [element("s1", "Cuenta", ["c1"])],
                "constraints": [],
                "data_bindings": [element("b1", "cliente en lakehouse", ["c1", "t1"]),
                                  element("b2", "cliente en ERP", ["c1", "t2"])],
            },
            "agent_context_pack": {"query_catalog": {"q": {"example_question": "Cuantos clientes activos hay?"}}},
        }

    def test_fabric_export_builds_valid_ontology_definition(self) -> None:
        export = build_platform_export(self._release("fabric"), "fabric", {"ontology_name": "Ventas ñ 2026"})
        files = export["files"]
        entity_paths = [path for path in files if "/EntityTypes/" in path]
        self.assertEqual(len(entity_paths), 2)
        entity = json.loads(files[entity_paths[0]])
        self.assertRegex(entity["name"], r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
        self.assertTrue(entity["id"].isdigit() and 0 < int(entity["id"]) < 2**63)
        self.assertIn("Ventas_n_2026.Ontology/.platform", " ".join(files))
        relation = json.loads(next(content for path, content in files.items() if "/RelationshipTypes/" in path))
        self.assertEqual({relation["source"]["entityTypeId"], relation["target"]["entityTypeId"]},
                         {json.loads(files[path])["id"] for path in entity_paths})
        request = json.loads(files["fabric/ontology/create_ontology_request.json"])
        decoded = {part["path"]: json.loads(base64.b64decode(part["payload"])) for part in request["definition"]["parts"]}
        self.assertEqual(decoded[".platform"]["metadata"]["type"], "Ontology")
        stage = json.loads(next(content for path, content in files.items() if path.endswith("stage_config.json")))
        self.assertIn("Un pedido anulado no cuenta como venta.", stage["aiInstructions"])
        self.assertIn("Cuenta", stage["aiInstructions"])
        self.assertEqual(export["summary"]["recommended_route"], "B")
        outside = [item for item in export["coverage"] if item["status"] == "outside_platform"]
        self.assertEqual({item["name"] for item in outside}, {"clientes", "cliente en ERP"})

    def test_databricks_export_builds_pages_metric_views_sql_and_genie_space(self) -> None:
        export = build_platform_export(self._release(), "databricks", {"catalog": "main", "warehouse_id": "abc123"})
        files = export["files"]
        self.assertIn("databricks/pages/cliente-activo.md", files)
        self.assertIn("**Sinonimos:** Cuenta", files["databricks/pages/cliente-activo.md"])
        self.assertIn("COMPLETAR_EXPRESION_AGREGADA", files["databricks/metric_views/ventas-netas.yaml"])
        sql = files["databricks/unity_catalog_comments.sql"]
        self.assertIn("COMMENT ON TABLE main.gold.dim_cliente IS 'Cliente activo: Cliente con compra en 12 meses.';", sql)
        self.assertNotIn("clientes", sql.split("\n", 3)[-1])
        request = json.loads(files["databricks/genie_agent_create_request.json"])
        self.assertEqual(request["warehouse_id"], "abc123")
        space = json.loads(request["serialized_space"])
        self.assertEqual(space["version"], 2)
        ids = [item["id"] for item in space["config"]["sample_questions"]]
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{32}", item) for item in ids))
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(space["data_sources"]["tables"][0]["identifier"], "main.gold.dim_cliente")
        self.assertEqual(len(space["instructions"]["text_instructions"]), 1)
        self.assertEqual(export["summary"]["recommended_route"], "B")

    def test_route_is_a_when_everything_is_reachable(self) -> None:
        release = self._release()
        release["canonical_ontology"]["technical_assets"] = release["canonical_ontology"]["technical_assets"][:1]
        release["canonical_ontology"]["data_bindings"] = release["canonical_ontology"]["data_bindings"][:1]
        export = build_platform_export(release, "databricks")
        self.assertEqual(export["summary"]["recommended_route"], "A")
        self.assertIn("Ruta recomendada: **A**", export["files"]["coverage_report.md"])


if __name__ == "__main__":
    unittest.main()
