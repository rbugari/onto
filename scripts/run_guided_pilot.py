"""Ejecucion guiada del piloto ONTO, paso a paso y con pausas de verificacion."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.models import utc_now_iso
from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore

PROJECT_ID = "fabric-gold-sic-risk-pilot"
PROJECT_NAME = "Fabric Gold SIC Risk Pilot"
PROJECT_DESCRIPTION = "Piloto guiado de ONTO sobre metadata Fabric y contexto de riesgo SIC."
DOCUMENTATION_DIR = ROOT_DIR / "data" / "context" / PROJECT_ID / "input" / "documentation"


def ask(message: str, *, default: bool = True) -> bool:
    suffix = "[Enter=si / n=no]" if default else "[s=si / Enter=no]"
    answer = input(f"\n{message} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in {"s", "si", "y", "yes"}


def pause(step: int, title: str, detail: str) -> None:
    print(f"\n{'=' * 72}\nPASO {step} - {title}\n{'=' * 72}")
    print(detail)
    input("\nPulsa Enter cuando hayas revisado la pantalla o el resultado para continuar...")


def reset_project_data(project_id: str) -> list[Path]:
    """Borra datos operativos del proyecto y conserva los documentos fuente."""
    data_dir = ROOT_DIR / "data"
    paths = [
        data_dir / "projects" / f"{project_id}.json",
        data_dir / "history" / project_id,
        data_dir / "context" / project_id / "output",
        data_dir / "context" / project_id / "working",
        data_dir / "context" / project_id / "evidence",
        data_dir / "fabric" / PROJECT_ID,
        data_dir / "registry" / PROJECT_ID,
        data_dir / "runtime" / PROJECT_ID,
        data_dir / "workspaces" / "fabric" / "gold-sic-risk",
    ]
    removed: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir():
            try:
                _remove_tree_windows_safe(path)
            except PermissionError as exc:
                raise PermissionError(
                    f"No se pudo limpiar {path}. Cierra Streamlit y pausa OneDrive "
                    "para esta carpeta; despues vuelve a ejecutar el runner."
                ) from exc
        else:
            _make_writable(path)
            path.unlink()
        removed.append(path)
    return removed


def _make_writable(path: Path) -> None:
    """Quita el atributo de solo lectura que OneDrive puede aplicar a placeholders."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def _remove_tree_windows_safe(path: Path) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["attrib", "-R", str(path), "/S", "/D"],
            check=False,
            capture_output=True,
        )

    def onexc(function, target, error):
        _make_writable(Path(target))
        function(target)

    shutil.rmtree(path, onexc=onexc)


def find_documents() -> list[Path]:
    if not DOCUMENTATION_DIR.exists():
        return []
    return sorted(path for path in DOCUMENTATION_DIR.iterdir() if path.is_file())


def print_json(label: str, value: object) -> None:
    print(f"\n{label}:\n{json.dumps(value, indent=2, ensure_ascii=False, default=str)}")


def run(args: argparse.Namespace) -> None:
    store = ProjectStore(ROOT_DIR / "data" / "projects")
    service = WorkbenchService(store)
    step = args.from_step

    if step <= 1:
        if not args.skip_reset:
            print("Este reset elimina los datos operativos del proyecto y conserva los documentos fuente.")
            if not ask("Confirmas el reset de fabric-gold-sic-risk-pilot?", default=False):
                raise SystemExit("Reset cancelado. No se modifico ningun dato.")
            removed = reset_project_data(PROJECT_ID)
            print(f"Reset terminado. Rutas eliminadas: {len(removed)}")
        else:
            print("Reset omitido por --skip-reset.")
        pause(1, "Reset verificado", "Comprueba en la web que el proyecto no tenga assessments, drafts ni releases.")

    if step <= 2:
        if args.skip_reset and store.project_exists(PROJECT_ID):
            project = service.get_project(PROJECT_ID)
            print(f"Proyecto existente reutilizado: {project.id}")
        else:
            project = service.create_project(PROJECT_NAME, PROJECT_DESCRIPTION)
            print(f"Proyecto creado: {project.id}")
        pause(2, "Proyecto creado", "En la web selecciona el proyecto nuevo y confirma que el estado inicial esta vacio.")
    else:
        project = service.get_project(PROJECT_ID)

    if step <= 3:
        if ask("Quieres comprobar la conexion real con Fabric ahora?", default=True):
            connection = service.check_fabric_connection()
            print_json("Conexion Fabric", connection)
            if connection.get("status") not in {"connected", "connected_read_only"}:
                print("La conexion no quedo conectada; puedes corregirla y reanudar con --from-step 3.")
                if not ask("Continuar sin Fabric?", default=False):
                    return
        else:
            print("Conexion Fabric omitida por decision del operador.")
        pause(3, "Fabric verificado", "En la web revisa que la conexion y el alcance read-only sean correctos.")

    if step <= 4:
        discovery = service.discover_fabric_metadata(PROJECT_ID)
        print(f"Metadata Fabric: {len(discovery.get('tables', []))} tablas, {len(discovery.get('columns', []))} columnas")
        imported = service.import_fabric_metadata(PROJECT_ID, discovery)
        print_json("Metadata incorporada a Atlas", imported)
        pause(4, "Inventario Fabric", "En Atlas confirma las tablas/columnas importadas y que no se leen filas de detalle.")

    if step <= 5:
        documents = find_documents()
        if not documents:
            raise SystemExit(f"No hay documentos en {DOCUMENTATION_DIR}")
        print("Documentos que se cargaran:")
        for path in documents:
            print(f" - {path.name}")
        if not ask("Confirmas cargar estos documentos?", default=True):
            raise SystemExit("Carga cancelada.")
        for path in documents:
            document = service.upload_context_document(
                PROJECT_ID, path.name, path.read_bytes(), "business_context", "application/octet-stream"
            )
            print(f"Cargado: {document.filename} ({document.extracted_chars} caracteres)")
        pause(5, "Documentos cargados", "En Workbench confirma nombres, cantidad y que la extraccion sea correcta.")

    if step <= 6:
        if not ask("Ejecutar el scanner de contexto en modo heuristico local?", default=True):
            raise SystemExit("Scanner cancelado.")
        inventory = service.scan_business_context(PROJECT_ID)
        print_json("Resumen de contexto", {
            "scan_mode": inventory.get("scan_mode"),
            "definitions": len(inventory.get("definitions", [])),
            "business_rules": len(inventory.get("business_rules", [])),
            "kpis": len(inventory.get("kpis", [])),
        })
        pause(6, "Contexto analizado", "En Atlas revisa el inventario, las reglas y los posibles gaps antes de regenerar el assessment.")

    if step <= 7:
        assessment = service.create_atlas_assessment(PROJECT_ID, "fabric", "gold-sic-risk", "risk")
        run_id = str(assessment["manifest"]["run_id"])
        print(f"Assessment creado: {run_id}")
        pause(7, "Assessment Atlas", "En Atlas revisa score y gaps. El script espera tu confirmacion antes de registrar la revision humana.")
        if not ask("Marcar el assessment como reviewed?", default=True):
            raise SystemExit(f"Assessment pendiente: {run_id}. Reanuda con --from-step 8.")
        review = service.update_atlas_review(
            PROJECT_ID, run_id, "reviewed", args.reviewer, args.reviewer_role,
            "Revision guiada del piloto: contexto y metadata Fabric comprobados.",
        )
        print_json("Revision Atlas", review)

    assessments = service.list_atlas_assessments(PROJECT_ID)
    assessment = assessments[0]
    run_id = str(assessment["run_id"])

    if step <= 8:
        draft = service.create_nexo_draft(PROJECT_ID, run_id)
        draft_id = str(draft["manifest"]["draft_id"])
        print(f"Draft Nexo creado: {draft_id}")
        print(f"Candidatos pendientes: {len(draft.get('candidates', []))}")
        pause(8, "Draft Nexo", "En Nexo revisa candidatos, evidencia y el alcance de la aprobacion masiva.")
    else:
        drafts = service.list_nexo_drafts(PROJECT_ID)
        draft_id = str(drafts[0]["draft_id"])

    if step <= 9:
        draft = service.get_nexo_draft(PROJECT_ID, draft_id)
        pending_candidates = [
            item for item in draft["candidates"] if item.get("status") == "pending_review"
        ]
        approved_candidates = []
        rejected_candidates = []
        for candidate in pending_candidates:
            evidence = candidate.get("evidence", {})
            evidence_available = str(evidence.get("evidence_status", "")) == "available"
            confidence = float(candidate.get("confidence", 0) or 0)
            candidate_type = str(candidate.get("candidate_type", ""))
            has_source = bool(str(evidence.get("source_document_id", "")).strip())
            if evidence_available and has_source and (
                candidate_type == "technical_asset" or confidence >= 0.75
            ):
                approved_candidates.append(str(candidate["candidate_id"]))
            else:
                rejected_candidates.append(str(candidate["candidate_id"]))

        print(f"Candidatos pendientes a decidir: {len(pending_candidates)}")
        print(f"Decision automatica del analista: {len(approved_candidates)} aprobados")
        print(f"Decision automatica del analista: {len(rejected_candidates)} rechazados")
        print("Regla: evidencia disponible + origen identificado; contexto con confianza >= 0.75; activos Fabric con metadata disponible.")
        if approved_candidates:
            approved_result = service.bulk_update_nexo_candidates(
                PROJECT_ID, draft_id, approved_candidates, "approved", args.reviewer, args.reviewer_role,
                "Aprobacion automatica del analista: evidencia disponible, origen identificado y confianza suficiente.",
            )
            print_json("Candidatos aprobados", approved_result)
        if rejected_candidates:
            rejected_result = service.bulk_update_nexo_candidates(
                PROJECT_ID, draft_id, rejected_candidates, "rejected", args.reviewer, args.reviewer_role,
                "Rechazo automatico del analista: evidencia insuficiente, origen no identificado o confianza inferior a 0.75.",
            )
            print_json("Candidatos rechazados", rejected_result)
        pause(9, "Decisiones Nexo aplicadas", "En Nexo confirma los contadores de aprobados y rechazados y revisa que no queden pendientes.")

    if step <= 10:
        release = service.publish_nexo_release(
            PROJECT_ID, draft_id, args.reviewer,
            "Release inicial del piloto generada por ejecucion guiada.",
        )
        release_id = str(release["manifest"]["release_id"])
        print(f"Release creada: {release_id}")
        pause(10, "Release emitida", "En Nexo confirma que la release existe y que Argos puede seleccionarla.")
    else:
        releases = service.list_nexo_releases(PROJECT_ID)
        release_id = str(releases[0]["release_id"])

    if step <= 11:
        questions = [
            "Cual es el riesgo de la regla 1003 en el SIC12?",
            "Cuantos riesgos hay?",
            "Cuantos valores REAL y DEFAULT hay?",
            "Que planeta es mas grande?",
        ]
        for question in questions:
            result = service.investigate_release(PROJECT_ID, release_id, question)
            print(f"\nPregunta: {question}\nEstado: {result['manifest']['status']}\nRespuesta: {result['answer']}")
        pause(11, "Argos probado", "En Argos repite las tres preguntas y comprueba answered para dominio y abstained fuera de evidencia.")

    print(f"\nPiloto guiado completado: {utc_now_iso()}")
    print(f"Proyecto: {PROJECT_ID}")
    print(f"Release: {release_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta ONTO paso a paso con confirmaciones humanas.")
    parser.add_argument("--skip-reset", action="store_true", help="No borrar datos operativos antes de empezar.")
    parser.add_argument("--from-step", type=int, default=1, choices=range(1, 12), help="Retomar desde un paso concreto.")
    parser.add_argument("--reviewer", default="rbugari.sop", help="Responsable de las decisiones.")
    parser.add_argument("--reviewer-role", default="Product Owner del piloto", help="Rol del responsable.")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
