"""Atlas demo over a distributed data estate: MariaDB ERP, Databricks lakehouse, Power BI and a CRM."""
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
from ontology_workbench.storage import ProjectStore


PROJECT_NAME = "Distribuidora - Ventas distribuidas"
PROJECT_ID = "distribuidora-ventas-distribuidas"
CLIENT_ID = "demo-distribuidora"
DOMAIN_ID = "comercial"
DATA_PRODUCT_ID = "ventas-distribuidas"
EXAMPLE_ROOT = ROOT_DIR / "examples" / "distributed_sales_demo" / "input"


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Atlas con sistemas distribuidos")
    parser.add_argument("--keep", action="store_true", help="No borrar artefactos previos de la demo")
    parser.add_argument("--allow-llm", action="store_true", help="Usar el proveedor LLM configurado")
    args = parser.parse_args()
    if not args.allow_llm:
        os.environ["ONTO_LLM_PROVIDER"] = "disabled"
    if not args.keep:
        reset_demo_artifacts()

    service = WorkbenchService(ProjectStore(ROOT_DIR / "data" / "projects"))
    project = service.create_project(
        PROJECT_NAME,
        "Caso sintetico: el dominio comercial vive en ERP, lakehouse, Power BI, CRM y planillas.",
        project_id=PROJECT_ID,
    )
    service.update_assessment_scope(
        project.id, CLIENT_ID, DOMAIN_ID, DATA_PRODUCT_ID, owner="Gerencia Comercial"
    )

    scope = json.loads((EXAMPLE_ROOT / "scope.json").read_text(encoding="utf-8"))
    source_ids: dict[str, str] = {}
    for item in scope["sources"]:
        source = service.register_data_source(
            project.id, item["name"], item["platform"], item["owner"], item["description"]
        )
        source_ids[item["key"]] = source.source_id
        if item["file"]:
            path = EXAMPLE_ROOT / item["file"]
            _, summary = service.import_source_metadata_file(
                project.id, source.source_id, path.name, path.read_bytes()
            )
            print(f"- {item['name']}: {summary['tables']} tablas, {summary['columns']} columnas")
        else:
            print(f"- {item['name']}: declarado sin metadata")

    for item in scope["use_cases"]:
        service.add_use_case(
            project.id,
            item["name"],
            item["business_question"],
            item["owner"],
            item["priority"],
            [source_ids[key] for key in item["sources"]],
        )

    for path in sorted((EXAMPLE_ROOT / "documentation").glob("*.md")):
        service.upload_context_document(
            project.id, path.name, path.read_bytes(), "functional_docs", "text/markdown"
        )
    service.scan_business_context(project.id)

    package = service.create_atlas_assessment(project.id, CLIENT_ID, DOMAIN_ID, DATA_PRODUCT_ID)
    score = package["readiness_score"]
    cross = package["cross_source_map"]
    print(f"\nAssessment: {package['manifest']['run_id']}")
    print(f"Score: {score['overall_score']}/5 ({score['interpretation']})")
    for dimension in score["dimensions"]:
        print(f"  {dimension['dimension']}: {dimension['score']}/5")
    print(
        f"Entidades compartidas: {cross['summary']['shared_entities']} "
        f"(con clave comun: {cross['summary']['shared_with_common_key']})"
    )
    for row in cross["shared_entities"]:
        print(f"  {row['entity']}: {', '.join(row['sources'])} -> {row['common_key'] or 'sin clave comun'}")
    print(f"Gaps: {len(package['gap_backlog'])}")
    for gap in package["gap_backlog"]:
        print(f"  [{gap['severity']}] {gap['gap_id']}")
    print(f"Paquete: {package['package_path']}")


def reset_demo_artifacts() -> None:
    (ROOT_DIR / "data" / "projects" / f"{PROJECT_ID}.json").unlink(missing_ok=True)
    for relative_path in (
        f"data/context/{PROJECT_ID}",
        f"data/history/{PROJECT_ID}",
        f"data/registry/{PROJECT_ID}",
        f"data/runtime/{PROJECT_ID}",
        f"data/interoperability/{PROJECT_ID}",
        f"data/workspaces/{CLIENT_ID}",
    ):
        shutil.rmtree(ROOT_DIR / relative_path, ignore_errors=True)


if __name__ == "__main__":
    main()
