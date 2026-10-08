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
from ontology_workbench.context_scanner import load_llm_settings


DEFAULT_PROJECT_ID = "fabric-gold-sic-risk-pilot"
DEFAULT_ABSTENTION_QUESTION = "Que planeta es mas grande?"


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo local de ONTO sobre una release aprobada")
    parser.add_argument("project_id", nargs="?", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--question", default="", help="Pregunta del dominio; por defecto usa el primer concepto")
    parser.add_argument("--skip-evaluation", action="store_true", help="No ejecutar la bateria Argos")
    parser.add_argument("--full-cycle", action="store_true", help="Ejecutar scanner y Atlas LLM, crear draft pendiente y probar la release ya aprobada")
    parser.add_argument("--max-calls", type=int, default=40, help="Presupuesto de llamadas para el contraste Atlas")
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
    cycle = None
    if args.full_cycle:
        settings = load_llm_settings()
        if not settings.enabled:
            raise SystemExit("El ciclo completo requiere un proveedor LLM habilitado.")
        print(f"Scanner LLM: {settings.provider} / {settings.deployment or settings.model}", flush=True)
        inventory = service.scan_business_context(args.project_id)
        if inventory.get("scan_mode") != settings.provider:
            raise SystemExit("El scanner no completo el modo LLM; revisar el inventario guardado antes de continuar.")
        project = service.get_project(args.project_id)
        print("Atlas: contraste documental e inferencias separadas...", flush=True)
        assessment = service.create_semantic_atlas_assessment(
            project.id, project.metadata.get("client_id") or project.id,
            project.metadata.get("domain_id") or "default",
            project.metadata.get("data_product_id") or project.id, max_calls=args.max_calls,
        )
        coverage = assessment["explanatory_coverage"]
        analysis = coverage["analysis"]
        print(f"Atlas: {analysis['status']} / {analysis['calls_made']} llamadas", flush=True)
        draft = service.create_nexo_draft(project.id, assessment["manifest"]["run_id"],
                                        source_authority="hybrid", query_catalog=context_pack.get("query_catalog", []))
        cycle = {
            "project_id": project.id, "provider": settings.provider, "model": settings.deployment or settings.model,
            "scanner_mode": inventory["scan_mode"], "assessment_run_id": assessment["manifest"]["run_id"],
            "atlas_status": analysis["status"], "atlas_calls": analysis["calls_made"],
            "coverage_groups": coverage["groups"], "inferred_explanations": len(coverage.get("inferred_explanations", [])),
            "inferences_count_as_documentary_support": False,
            "draft_id": draft["manifest"]["draft_id"], "draft_summary": draft["manifest"]["candidate_summary"],
            "new_release_published": False, "new_knowledge_review_status": "pending_review",
            "argos_tested_release_id": release_id, "argos_uses_new_draft": False,
        }
        print(f"Nexo: {cycle['draft_id']} pendiente de revision, sin aprobacion automatica", flush=True)
        print(f"Inferencias separadas: {cycle['inferred_explanations']}", flush=True)

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
    if cycle is not None:
        cycle["domain_question_status"] = answered["manifest"]["status"]
        cycle["outside_evidence_status"] = abstained["manifest"]["status"]

    if not args.skip_evaluation:
        cases = service.suggest_argos_evaluation_cases(args.project_id, release_id)
        evaluation = service.evaluate_argos_release(args.project_id, release_id, cases)
        print(
            f"\nEvaluacion Argos: {evaluation['summary']['passed']}/"
            f"{evaluation['summary']['total']} casos OK"
        )
        print(f"Paquete de evaluacion: {evaluation['package_path']}")
        if cycle is not None:
            cycle["argos_evaluation"] = evaluation["summary"]
            cycle["argos_evaluation_path"] = evaluation["package_path"]
    if cycle is not None:
        cycle["platform_exports"] = {}
        for target in service.interoperability_targets():
            package = service.prepare_interoperability_package(
                args.project_id, release_id, target, "ONTO dev verification",
                "Exportacion de la release existente; el nuevo draft LLM sigue pendiente de revision.",
            )
            cycle["platform_exports"][target] = package["package_path"]
            print(f"Paquete {target}: {package['package_path']}", flush=True)
        summary_path = Path(assessment["package_path"]) / "llm_cycle_summary.json"
        summary_path.write_text(json.dumps(cycle, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Resumen del ciclo: {summary_path}", flush=True)


if __name__ == "__main__":
    main()
