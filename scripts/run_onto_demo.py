"""Run the local ONTO demo against an existing approved release."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore


DEFAULT_PROJECT_ID = "fabric-gold-sic-risk-pilot"
DEFAULT_ABSTENTION_QUESTION = "Que planeta es mas grande?"


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo local de ONTO sobre una release aprobada")
    parser.add_argument("project_id", nargs="?", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--question", default="", help="Pregunta del dominio; por defecto usa el primer concepto")
    parser.add_argument("--skip-evaluation", action="store_true", help="No ejecutar la bateria Argos")
    args = parser.parse_args()

    service = WorkbenchService(ProjectStore(ROOT_DIR / "data" / "projects"))
    releases = service.store.list_nexo_releases(args.project_id)
    if not releases:
        raise SystemExit(f"No hay releases Nexo para el proyecto: {args.project_id}")
    release = releases[0]
    release_id = str(release["release_id"])
    package_path = Path(str(release["package_path"]))
    context_pack = json.loads((package_path / "agent_context_pack.json").read_text(encoding="utf-8"))
    concepts = [item for item in context_pack.get("concepts", []) if isinstance(item, dict)]
    question = args.question.strip() or (f"Que es {concepts[0]['name']}?" if concepts else "Que define la release?")

    print("ONTO - Demo local")
    print(f"Proyecto: {args.project_id}")
    print(f"Release: {release_id}")
    print(f"Conceptos: {len(context_pack.get('concepts', []))}")
    print(f"Reglas: {len(context_pack.get('business_rules', []))}")
    print(f"KPIs: {len(context_pack.get('kpis', []))}")
    print(f"Bindings: {len(context_pack.get('data_bindings', []))}")
    print(f"Contrato: {context_pack['query_contract']['allowed_operations']} read-only")

    answered = service.investigate_release(args.project_id, release_id, question)
    abstained = service.investigate_release(args.project_id, release_id, DEFAULT_ABSTENTION_QUESTION)
    print(f"\nPregunta de dominio: {answered['manifest']['status']}")
    print(f"Respuesta: {answered['answer']}")
    print(f"Pregunta fuera de evidencia: {abstained['manifest']['status']}")
    print(f"Respuesta: {abstained['answer']}")

    if not args.skip_evaluation:
        cases = service.suggest_argos_evaluation_cases(args.project_id, release_id)
        evaluation = service.evaluate_argos_release(args.project_id, release_id, cases)
        print(
            f"\nEvaluacion Argos: {evaluation['summary']['passed']}/"
            f"{evaluation['summary']['total']} casos OK"
        )
        print(f"Paquete de evaluacion: {evaluation['package_path']}")


if __name__ == "__main__":
    main()
