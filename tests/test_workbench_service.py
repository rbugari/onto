from __future__ import annotations

import sys
import unittest
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore
from ontology_workbench.context_scanner import CONTEXT_CHUNK_SIZE, build_document_chunks, load_llm_settings
from ontology_workbench.nexo_diff import compare_nexo_artifacts
from ontology_workbench.fabric_adapter import load_fabric_settings


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
        technical_source = assessment["source_inventory"]["technical_sources"][0]
        self.assertEqual(technical_source["source_format"], "fabric-information-schema")
        self.assertTrue(technical_source["content_sha256"])
        draft = self.service.create_nexo_draft(project.id, str(assessment["manifest"]["run_id"]))
        self.assertEqual(
            len([item for item in draft["candidates"] if item["candidate_type"] == "technical_asset"]),
            3,
        )

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
        answer = self.service.investigate_release(project.id, str(release["manifest"]["release_id"]), "Que es Cliente Activo?")
        abstention = self.service.investigate_release(project.id, str(release["manifest"]["release_id"]), "Que planeta es mas grande?")
        self.assertEqual(answer["manifest"]["status"], "answered")
        self.assertEqual(abstention["manifest"]["status"], "abstained")
        evaluation_cases = self.service.suggest_argos_evaluation_cases(
            project.id, str(release["manifest"]["release_id"])
        )
        evaluation = self.service.evaluate_argos_release(
            project.id, str(release["manifest"]["release_id"]), evaluation_cases
        )
        self.assertEqual(evaluation["summary"]["failed"], 0)
        self.assertTrue(Path(str(evaluation["package_path"])).exists())

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


if __name__ == "__main__":
    unittest.main()
