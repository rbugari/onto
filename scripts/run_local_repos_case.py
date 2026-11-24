"""Atlas -> Nexo -> platform packages over real repositories found on disk.

Case A: Nalub legacy (MariaDB schema from the backup) + Nalub Pedidos app (db.sql + its docs).
Case B: TestData DW (SQL Server DDL project used as a Fabric warehouse test).
Sources outside this repo are optional: a missing path skips its case. Writes under ONTO_DATA_DIR (default ./data).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore

DATA_DIR = Path(os.environ.get("ONTO_DATA_DIR", ROOT_DIR / "data"))
LEGACY_SCHEMA = ROOT_DIR / "docs" / "casos" / "nalub_mariadb" / "input" / "nalub_schema.sql"
PEDIDOS_DOCS = ("DATABASE.md", "FEATURES.md", "ARCHITECTURE.md", "README.md")
REVIEWER = ("Revisor de prueba", "Datos")


def main() -> None:
    parser = argparse.ArgumentParser(description="Casos Atlas/Nexo sobre repositorios locales")
    parser.add_argument("--pedidos-repo", default=r"C:\proyectos_dev\nalubPedidos")
    parser.add_argument("--dw-repo", default=r"C:\Fabric\testDataDW")
    parser.add_argument("--case", choices=["all", "nalub", "dw"], default="all")
    parser.add_argument("--allow-llm", action="store_true", help="Usar el proveedor LLM configurado")
    args = parser.parse_args()
    if not args.allow_llm:
        os.environ["ONTO_LLM_PROVIDER"] = "disabled"
    service = WorkbenchService(ProjectStore(DATA_DIR / "projects"))
    if args.case in {"all", "nalub"}:
        run_nalub(service, Path(args.pedidos_repo))
    if args.case in {"all", "dw"}:
        run_dw(service, Path(args.dw_repo))


def run_nalub(service: WorkbenchService, pedidos: Path) -> None:
    db_sql, docs = pedidos / "db.sql", pedidos / "docs"
    if not (db_sql.exists() and LEGACY_SCHEMA.exists()):
        print(f"[nalub] omitido: falta {db_sql} o {LEGACY_SCHEMA}")
        return
    project = _new_project(service, "nalub-multisistema", "Nalub - legacy y Pedidos", "Dos sistemas MariaDB del mismo negocio.")
    legacy = service.register_data_source(project.id, "Nalub legacy", "mariadb", "Sistemas Nalub")
    app = service.register_data_source(project.id, "Nalub Pedidos (app)", "mariadb", "Desarrollo Nalub")
    for source, path in ((legacy, LEGACY_SCHEMA), (app, db_sql)):
        _, summary = service.import_source_metadata_file(project.id, source.source_id, path.name, path.read_bytes())
        print(f"- {source.name}: {summary['tables']} tablas, {summary['columns']} columnas")
    service.add_use_case(
        project.id, "Pedidos y deuda por cliente", "Que clientes tienen pedidos pendientes y deuda?",
        "Comercial", "alta", [legacy.source_id, app.source_id],
    )
    for name in PEDIDOS_DOCS:
        if (docs / name).exists():
            service.upload_context_document(project.id, name, (docs / name).read_bytes(), "functional_docs", "text/markdown")
    service.scan_business_context(project.id)
    _assess_and_deliver(service, project.id, "nalub", "pedidos")


def run_dw(service: WorkbenchService, dw: Path) -> None:
    tables = sorted((dw / "dbo").rglob("*.sql"))
    if not tables:
        print(f"[dw] omitido: no hay DDL en {dw}")
        return
    project = _new_project(service, "taxi-dw-fabric", "TestData DW (taxis)", "Warehouse de prueba en SQL Server/Fabric.")
    source = service.register_data_source(project.id, "TestData DW", "fabric", "Datos")
    ddl = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in tables)
    _, summary = service.import_source_metadata_file(project.id, source.source_id, "testdata_dw.sql", ddl.encode("utf-8"))
    print(f"- {source.name}: {summary['tables']} tablas, {summary['columns']} columnas")
    service.add_use_case(project.id, "Analisis de viajes", "Cuanto se recauda por tipo de pago?", "Operaciones", "media", [source.source_id])
    _assess_and_deliver(service, project.id, "taxi", "viajes")


def _new_project(service: WorkbenchService, project_id: str, name: str, description: str):
    unique_id, number = project_id, 2
    while service.store.project_exists(unique_id):
        unique_id, number = f"{project_id}-{number}", number + 1
    project = service.create_project(name, description, project_id=unique_id)
    service.update_assessment_scope(project.id, f"{project_id}-client", "operacion", project_id, owner="Equipo de pruebas")
    print(f"\n== {name} ({project.id})")
    return project


def _assess_and_deliver(service: WorkbenchService, project_id: str, client: str, product: str) -> None:
    package = service.create_atlas_assessment(project_id, f"{client}-client", "operacion", product)
    cross, coverage = package["cross_source_map"], package["platform_coverage"]
    print(f"Atlas: score {package['readiness_score']['overall_score']}/5, {len(package['gap_backlog'])} brechas, "
          f"{cross['summary']['shared_entities']} entidades compartidas")
    for target, route in coverage["routes"].items():
        print(f"  ruta {target}: {route['route']} ({route['tables_total'] - route['tables_outside']}/{route['tables_total']} tablas)")
    print(f"  capas: {coverage['summary']['layers']}")
    run_id = str(package["manifest"]["run_id"])
    draft = service.create_nexo_draft(project_id, run_id, source_authority="technical")
    draft_id = str(draft["manifest"]["draft_id"])
    service.bulk_update_nexo_candidates(
        project_id, draft_id, [str(item["candidate_id"]) for item in draft["candidates"]],
        "approved", REVIEWER[0], REVIEWER[1], "Aprobado solo para la prueba con repositorios locales.",
    )
    release = service.publish_nexo_release(project_id, draft_id, REVIEWER[0], "Release de prueba.")
    release_id = str(release["manifest"]["release_id"])
    for target, settings in (("fabric", {}), ("databricks", {"catalog": "main"})):
        export = service.prepare_interoperability_package(project_id, release_id, target, REVIEWER[0], "Paquete de prueba.", settings)
        summary = export["export"]["summary"]
        print(f"Nexo -> {summary['target_label']}: ruta {summary['recommended_route']}, "
              f"{summary['implementable_in_platform']}/{summary['total']} implementables, "
              f"pendientes {summary['pending_completion']} -> {export['package_path']}")


if __name__ == "__main__":
    main()
