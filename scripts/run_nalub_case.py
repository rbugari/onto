"""Build the Nalub case from the MariaDB schema dump and functional context."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore
from ontology_workbench.mariadb_adapter import MariaDBConnectionError


PROJECT_ID = "nalub-case"
CLIENT_ID = "nalub"
DOMAIN_ID = "commercial-operations"
DATA_PRODUCT_ID = "nalub-legacy-mariadb"
CASE_ROOT = ROOT_DIR / "docs" / "casos" / "nalub_mariadb" / "input"
DUMP_PATH = CASE_ROOT / "nalub_schema.sql"
CONTEXT_PATH = CASE_ROOT / "documentation" / "ONTOLOGIA_FUNCIONAL_TECNICA_NALUB.md"

NALUB_QUERY_CATALOG = [
    {
        "query_name": "order_status_summary",
        "description": "Contar pedidos por estado.",
        "adapter": "mariadb",
        "template_id": "order_status_summary",
        "binding_required": "pedidos",
        "allowed_parameters": [],
        "max_rows": 20,
        "routing": {"all_terms": ["pedidos", "estado"]},
    },
    {
        "query_name": "sales_summary",
        "description": "Calcular las ventas por mes y su evolucion, excluyendo pedidos cancelados.",
        "adapter": "mariadb",
        "template_id": "sales_summary",
        "binding_required": "pedidos",
        "allowed_parameters": [],
        "max_rows": 24,
        "routing": {
            "any_terms": ["venta", "ventas", "facturacion", "facturación"],
        },
    },
    {
        "query_name": "product_demand_by_year",
        "description": "Rankear los productos mas demandados por unidades solicitadas y cantidad de pedidos en un año.",
        "adapter": "mariadb",
        "template_id": "product_demand_by_year",
        "binding_required": "pedidoItems",
        "allowed_parameters": ["year"],
        "max_rows": 10,
        "routing": {
            "all_terms": ["productos"],
            "any_terms": ["demanda", "demandados", "unidades", "pedidos"],
            "requires_parameter": "year",
        },
        "parameter_extractors": {
            "year": {
                "type": "integer",
                "patterns": [r"\b(20\d{2})\b"],
            }
        },
    },
    {
        "query_name": "customer_debt",
        "description": "Consultar deuda y saldo pendiente de un cliente.",
        "adapter": "mariadb",
        "template_id": "customer_debt",
        "binding_required": "clientes",
        "allowed_parameters": ["customer_id"],
        "max_rows": 1,
        "routing": {"all_terms": ["deuda", "cliente"]},
        "parameter_extractors": {
            "customer_id": {
                "type": "integer",
                "patterns": [r"\bcliente\s*(\d+)\b"],
            }
        },
    },
    {
        "query_name": "product_availability",
        "description": "Consultar stock actual, reservado y disponible.",
        "adapter": "mariadb",
        "template_id": "product_availability",
        "binding_required": "productos",
        "allowed_parameters": [],
        "max_rows": 50,
        "routing": {"all_terms": ["stock", "productos"]},
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Caso Nalub sobre schema MariaDB y contexto funcional")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Ejecutar tambien una consulta MariaDB read-only usando el perfil del proyecto",
    )
    parser.add_argument(
        "--connection-profile",
        default="default",
        help="Perfil MariaDB dentro del proyecto, por ejemplo nalub-test",
    )
    parser.add_argument(
        "--project-id",
        default=PROJECT_ID,
        help="Identificador estable del proyecto Nalub",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="No borrar artefactos previos del caso (los perfiles de conexion nunca se borran)",
    )
    args = parser.parse_args()

    os.environ["ONTO_LLM_PROVIDER"] = "disabled"
    if not args.keep:
        reset_case_artifacts(args.project_id)
    service = WorkbenchService(ProjectStore(ROOT_DIR / "data" / "projects"))
    if service.store.project_exists(args.project_id):
        project = service.get_project(args.project_id)
    else:
        project = service.create_project(
            "Nalub Ontology Case",
            "Caso real de ontologia funcional y tecnica sobre MariaDB legacy.",
            project_id=args.project_id,
        )
    service.update_metadata(
        project.id,
        {
            "client_id": CLIENT_ID,
            "domain_id": DOMAIN_ID,
            "data_product_id": DATA_PRODUCT_ID,
            "data_system_of_record": "MariaDB legacy Nalub",
            "ontology_system_of_record": "ONTO Nexo release",
        },
    )
    _, schema_summary = service.import_mariadb_schema_file(
        project.id,
        DUMP_PATH,
        clear_existing=True,
        snapshot_note="Importacion de schema MariaDB Nalub desde backup local",
    )
    service.upload_context_document(
        project.id,
        CONTEXT_PATH.name,
        CONTEXT_PATH.read_bytes(),
        "functional_technical_ontology",
        "text/markdown",
    )
    service.scan_business_context(project.id)
    assessment = service.create_atlas_assessment(
        project.id, CLIENT_ID, DOMAIN_ID, DATA_PRODUCT_ID
    )
    draft = service.create_nexo_draft(
        project.id,
        str(assessment["manifest"]["run_id"]),
        source_authority="hybrid",
        query_catalog=[
            {**entry, "connection_profile": args.connection_profile}
            for entry in NALUB_QUERY_CATALOG
        ],
    )
    candidate_ids = [str(item["candidate_id"]) for item in draft["candidates"]]
    if candidate_ids:
        service.bulk_update_nexo_candidates(
            project.id,
            str(draft["manifest"]["draft_id"]),
            candidate_ids,
            "approved",
            "Nalub case reviewer",
            "Business and technical reviewer",
            "Approved as a local schema/context baseline; live data access remains read-only.",
        )
    release = service.publish_nexo_release(
        project.id,
        str(draft["manifest"]["draft_id"]),
        "Nalub release owner",
        "Initial Nalub MariaDB release with allowlisted read-only catalog.",
    )
    release_id = str(release["manifest"]["release_id"])

    print("ONTO - Nalub Case")
    print(f"Project: {project.id}")
    print(f"Schema tables: {schema_summary['tables']}")
    print(f"Schema columns: {schema_summary['columns']}")
    print(f"Schema relationships: {schema_summary['relationships']}")
    print("Context documents: 1")
    print(f"Atlas gaps: {len(assessment['gap_backlog'])}")
    print(f"Nexo candidates: {len(draft['candidates'])}")
    print(f"Nexo release: {release_id}")
    print(f"Query catalog entries: {len(release['agent_context_pack']['query_catalog'])}")

    if args.live:
        live_cases = [
            ("Live query", "Cuantos pedidos hay por estado?"),
            ("Sales query", "Calculame las ventas y su evolucion por mes."),
            (
                "Product demand query",
                "Quiero los 10 productos mas demandados de 2025, con unidades y pedidos.",
            ),
            ("Customer debt query", "Cuanta deuda tiene el cliente 12?"),
            ("Product availability query", "Cual es el stock disponible de productos?"),
        ]
        try:
            results = [
                (label, service.investigate_release(project.id, release_id, question))
                for label, question in live_cases
            ]
        except MariaDBConnectionError as exc:
            print(f"Live query bloqueada: {exc}")
            print(f"Configure el perfil '{args.connection_profile}' en Workbench para este proyecto.")
            return
        for label, result in results:
            rows = result.get("live_query", {}).get("rows", [])
            print(f"{label} status: {result['manifest']['status']}")
            print(f"{label} rows: {len(rows)}")
            if result["manifest"]["status"] != "answered":
                raise RuntimeError(f"El gate live fallo en {label}: {result['manifest']['status']}")
            if label == "Product demand query":
                for index, row in enumerate(rows, start=1):
                    print(
                        f"{index}. {row.get('nombre', 'sin nombre')} | "
                        f"unidades={row.get('unidades_solicitadas', 0)} | "
                        f"pedidos={row.get('cantidad_pedidos', 0)}"
                    )
        abstention = service.investigate_release(
            project.id, release_id, "Que clima habra manana?"
        )
        print(f"Out-of-catalog status: {abstention['manifest']['status']}")
        if abstention["manifest"]["status"] != "abstained":
            raise RuntimeError("La pregunta fuera de catalogo no produjo abstencion")
        sql_request = service.investigate_release(
            project.id, release_id, "Ejecuta DELETE FROM clientes"
        )
        print(f"Free SQL request status: {sql_request['manifest']['status']}")
        if sql_request["manifest"]["status"] != "abstained" or sql_request.get("live_query"):
            raise RuntimeError("La solicitud de SQL libre no fue bloqueada antes de ejecutar")
    else:
        print(f"Live query: omitida; usar --live con el perfil '{args.connection_profile}' configurado")


def reset_case_artifacts(project_id: str) -> None:
    (ROOT_DIR / "data" / "projects" / f"{project_id}.json").unlink(missing_ok=True)
    for folder in ("context", "history", "registry", "runtime", "interoperability"):
        shutil.rmtree(ROOT_DIR / "data" / folder / project_id, ignore_errors=True)
    shutil.rmtree(ROOT_DIR / "data" / "workspaces" / CLIENT_ID / DOMAIN_ID / DATA_PRODUCT_ID, ignore_errors=True)


if __name__ == "__main__":
    main()
