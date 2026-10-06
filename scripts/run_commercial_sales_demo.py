"""Run the synthetic commercial sales demo through Atlas, Nexo and Argos."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore, unique_file_paths_by_content


PROJECT_ID = "commercial-sales-demo"
CLIENT_ID = "demo-client"
DOMAIN_ID = "commercial-sales"
DATA_PRODUCT_ID = "sales-analytics"
EXAMPLE_ROOT = ROOT_DIR / "docs" / "casos" / "comercial_powerbi"

COMMERCIAL_QUERY_CATALOG = [
    {
        "query_name": "sales_by_customer",
        "description": "Ventas de un cliente.",
        "example_question": "¿Cuántas ventas tiene el cliente 42?",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo sintetica comercial de ONTO")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="No limpiar artefactos previos del proyecto demo antes de ejecutar",
    )
    parser.add_argument(
        "--allow-llm",
        action="store_true",
        help="Permitir el proveedor LLM configurado; por defecto usa modo heuristico",
    )
    args = parser.parse_args()

    if not args.allow_llm:
        os.environ["ONTO_LLM_PROVIDER"] = "disabled"
    if not args.keep:
        reset_demo_artifacts()

    service = WorkbenchService(ProjectStore(ROOT_DIR / "data" / "projects"))
    project = service.create_project(
        "Commercial Sales Demo",
        "Caso sintetico comercial para validar Atlas, Nexo y Argos.",
    )
    project = service.update_metadata(
        project.id,
        {
            "client_id": CLIENT_ID,
            "domain_id": DOMAIN_ID,
            "data_product_id": DATA_PRODUCT_ID,
            "demo_data": "synthetic",
        },
    )

    model_path = EXAMPLE_ROOT / "input" / "model.bim"
    imported_project, model_summary = service.import_bim_file(
        project.id, model_path.name, model_path.read_bytes(), clear_existing=True
    )
    all_document_paths = sorted((EXAMPLE_ROOT / "input" / "documentation").glob("*.md"))
    document_paths = unique_file_paths_by_content(all_document_paths)
    for document_path in document_paths:
        service.upload_context_document(
            project.id,
            document_path.name,
            document_path.read_bytes(),
            "functional_docs",
            "text/markdown",
        )
    service.scan_business_context(project.id)
    assessment = service.create_atlas_assessment(
        project.id, CLIENT_ID, DOMAIN_ID, DATA_PRODUCT_ID
    )
    draft = service.create_nexo_draft(
        project.id,
        str(assessment["manifest"]["run_id"]),
        source_authority="documentation",
        query_catalog=COMMERCIAL_QUERY_CATALOG,
    )
    draft_id = str(draft["manifest"]["draft_id"])
    candidate_ids = [str(item["candidate_id"]) for item in draft["candidates"]]
    if candidate_ids:
        service.bulk_update_nexo_candidates(
            project.id,
            draft_id,
            candidate_ids,
            "approved",
            "Demo reviewer",
            "Business and technical reviewer",
            "Approved for synthetic demo only; requires real-domain review.",
        )
    release = service.publish_nexo_release(
        project.id,
        draft_id,
        "Demo release owner",
        "Synthetic commercial sales release.",
    )
    release_id = str(release["manifest"]["release_id"])
    mapping = service.prepare_interoperability_package(
        project.id,
        release_id,
        "fabric",
        "Demo release owner",
        "Mapping prepared for review; no external publication.",
    )
    answered = service.investigate_release(
        project.id, release_id, "Que es Cliente activo?"
    )
    commercial_query = service.investigate_release(
        project.id, release_id, "Cuantas ventas tiene el cliente 42?"
    )
    abstained = service.investigate_release(
        project.id, release_id, "Que planeta es mas grande?"
    )
    evaluation = service.evaluate_argos_release(
        project.id,
        release_id,
        [
            {
                "question": "Que es Cliente activo?",
                "expected_status": "answered",
                "expected_evidence_name": "Cliente activo",
            },
            {
                "question": "Que planeta es mas grande?",
                "expected_status": "abstained",
                "expected_evidence_name": "",
            },
        ],
    )

    print("ONTO - Commercial Sales Demo")
    print(f"Project: {project.id}")
    print(f"Assessment: {assessment['manifest']['run_id']}")
    print(f"Technical tables: {model_summary['tables']}")
    print(f"Technical columns: {model_summary['columns']}")
    print(f"Documents: {len(document_paths)} unique of {len(all_document_paths)}")
    print(f"Atlas gaps: {len(assessment['gap_backlog'])}")
    print(f"Nexo candidates: {len(draft['candidates'])}")
    print(f"Nexo release: {release_id}")
    print(f"Query catalog entries: {len(release['agent_context_pack']['query_catalog'])}")
    print(f"Mapping: {mapping['package_path']}")
    print(f"Argos answered: {answered['manifest']['status']}")
    print(f"Commercial query: {commercial_query['manifest']['status']}")
    print(f"Commercial rows: {len(commercial_query['live_query']['rows'])}")
    print(f"Argos abstention: {abstained['manifest']['status']}")
    print(
        f"Evaluation: {evaluation['summary']['passed']}/"
        f"{evaluation['summary']['total']} cases OK"
    )


def reset_demo_artifacts() -> None:
    project_file = ROOT_DIR / "data" / "projects" / f"{PROJECT_ID}.json"
    project_file.unlink(missing_ok=True)
    for relative_path in (
        f"data/context/{PROJECT_ID}",
        f"data/registry/{PROJECT_ID}",
        f"data/runtime/{PROJECT_ID}",
        f"data/interoperability/{PROJECT_ID}",
    ):
        shutil.rmtree(ROOT_DIR / relative_path, ignore_errors=True)
    workspace_root = ROOT_DIR / "data" / "workspaces"
    for candidate in workspace_root.glob(f"{CLIENT_ID}/{DOMAIN_ID}/{DATA_PRODUCT_ID}"):
        shutil.rmtree(candidate, ignore_errors=True)


if __name__ == "__main__":
    main()
