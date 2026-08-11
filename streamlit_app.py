from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore
from ontology_workbench.context_scanner import SUPPORTED_DOCUMENT_TYPES, SUPPORTED_FILE_EXTENSIONS, load_llm_settings


store = ProjectStore(ROOT_DIR / "data" / "projects")
service = WorkbenchService(store)


PRODUCT_AREAS = {
    "Inicio": "Inicio",
    "Atlas": "Atlas · Preparación analítica",
    "Nexo": "Nexo · Gobierno y publicación",
    "Argos": "Argos · Análisis de negocio",
    "Workbench": "Workbench",
}


def render_project_selector() -> str | None:
    projects = service.list_projects()
    if not projects:
        st.sidebar.info("No hay proyectos todavia. Crea uno para empezar.")
        return None

    labels = {project.id: project.name for project in projects}
    selected_id = st.sidebar.selectbox(
        "Proyecto",
        options=list(labels.keys()),
        format_func=lambda item: labels[item],
    )
    return selected_id


def open_product_area(area: str) -> None:
    st.session_state["active_product_area"] = area


def render_factory_home(project) -> None:
    st.title("DataIA Ontology Factory")
    st.caption("Una ruta local y gobernada desde evidencia hasta investigación sobre releases.")
    st.info(
        f"Proyecto activo: {project.name}. Selecciona un producto para continuar; todos comparten "
        "el mismo proyecto local, pero sus datos y decisiones permanecen separados por contrato."
    )
    products = [
        (
            "Atlas",
            "Atlas · Ontology Readiness Assessment",
            "Lo usan analistas de negocio y sistemas para preparar evidencia, contexto y gaps.",
            "Producto 1 · Preparación para analistas",
            "Abrir Atlas",
        ),
        (
            "Nexo",
            "Nexo · Registry & Validation",
            "Lo usan analistas para gobernar hallazgos, validar decisiones y publicar releases.",
            "Producto 2 · Gobierno para analistas",
            "Abrir Nexo",
        ),
        (
            "Argos",
            "Argos · Análisis de negocio",
            "Lo usa el negocio para obtener respuestas y números accionables sobre problemas reales.",
            "Producto 3 · Superficie de negocio",
            "Abrir Argos",
        ),
    ]
    columns = st.columns(3)
    for column, (area, title, description, status, action) in zip(columns, products):
        with column:
            with st.container(border=True):
                st.subheader(title)
                st.caption(status)
                st.write(description)
                st.button(action, key=f"home-open-{area}", on_click=open_product_area, args=(area,), use_container_width=True)

    st.divider()
    workbench_column, status_column = st.columns((2, 3))
    with workbench_column:
        st.subheader("Workbench operativo")
        st.write("Importa modelos, carga documentos, edita metadata y administra conceptos o relaciones del proyecto.")
        st.button("Abrir Workbench", on_click=open_product_area, args=("Workbench",), use_container_width=True)
    with status_column:
        assessments = service.list_atlas_assessments(project.id)
        drafts = service.list_nexo_drafts(project.id)
        releases = service.list_nexo_releases(project.id)
        metrics = st.columns(3)
        metrics[0].metric("Assessments", len(assessments))
        metrics[1].metric("Drafts Nexo", len(drafts))
        metrics[2].metric("Releases", len(releases))
        completed_steps = sum(bool(items) for items in (assessments, drafts, releases))
        st.subheader("Progreso del piloto")
        st.progress(completed_steps / 3, text=f"{completed_steps} de 3 etapas completadas")
        progress_columns = st.columns(3)
        progress_columns[0].write(f"{'OK' if assessments else 'Pendiente'} · Atlas\nAssessment revisado")
        progress_columns[1].write(f"{'OK' if drafts else 'Pendiente'} · Nexo\nDraft validado")
        progress_columns[2].write(f"{'OK' if releases else 'Pendiente'} · Argos\nContexto disponible")
        if releases:
            st.success("El piloto esta listo para ejecutar consultas controladas en Argos.")
        elif drafts:
            st.warning("Siguiente paso: revisar los candidatos pendientes y emitir una release Nexo.")
        elif assessments:
            st.warning("Siguiente paso: crear un draft Nexo a partir del assessment Atlas.")
        else:
            st.info("Siguiente paso: conectar una fuente, inventariar sus activos y generar un assessment Atlas.")


def render_create_project() -> None:
    with st.sidebar.form("create-project", clear_on_submit=True):
        st.subheader("Nuevo proyecto")
        project_name = st.text_input("Nombre")
        project_description = st.text_area("Descripcion")
        submitted = st.form_submit_button("Crear proyecto")
        if submitted:
            try:
                project = service.create_project(project_name, project_description)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["selected_project_id"] = project.id
                st.rerun()

    with st.sidebar.expander("Importar proyecto"):
        uploaded_file = st.file_uploader("Archivo JSON exportado", type=["json"])
        preserve_project_id = st.checkbox("Preservar id si esta libre", value=False)
        if uploaded_file is not None and st.button("Importar JSON"):
            try:
                payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
                project = service.import_project(payload, preserve_project_id=preserve_project_id)
            except (ValueError, json.JSONDecodeError) as exc:
                st.error(str(exc))
            else:
                st.session_state["selected_project_id"] = project.id
                st.success("Proyecto importado")
                st.rerun()


def render_project_overview(project_id: str, project) -> None:
    issues = service.validate_project(project_id)
    metrics = st.columns(4)
    metrics[0].metric("Conceptos", len(project.concepts))
    metrics[1].metric("Relaciones", len(project.relations))
    metrics[2].metric("Errores", sum(1 for issue in issues if issue.level == "error"))
    metrics[3].metric("Warnings", sum(1 for issue in issues if issue.level == "warning"))

    with st.expander("Validacion estructural", expanded=True):
        if not issues:
            st.success("No se detectaron observaciones estructurales.")
        else:
            for issue in issues:
                if issue.level == "error":
                    st.error(f"{issue.code}: {issue.message}")
                elif issue.level == "warning":
                    st.warning(f"{issue.code}: {issue.message}")
                else:
                    st.info(f"{issue.code}: {issue.message}")


def render_atlas_assessment(project_id: str, project) -> None:
    st.subheader("Atlas · Ontology Readiness Assessment")
    st.caption(
        "Genera un baseline reproducible de inventario, contexto, score y gaps. "
        "No aprueba una ontologia ni publica cambios en sistemas externos."
    )
    default_client = project.metadata.get("client_id", project.id)
    default_domain = project.metadata.get("domain_id", "default")
    default_data_product = project.metadata.get("data_product_id", project.id)
    with st.form(f"atlas-assessment-{project_id}"):
        columns = st.columns(3)
        client_id = columns[0].text_input("Cliente", value=default_client)
        domain_id = columns[1].text_input("Dominio", value=default_domain)
        data_product_id = columns[2].text_input("Data product", value=default_data_product)
        submitted = st.form_submit_button("Generar assessment Atlas")
        if submitted:
            try:
                package = service.create_atlas_assessment(
                    project_id,
                    client_id=client_id,
                    domain_id=domain_id,
                    data_product_id=data_product_id,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                score = dict(package["readiness_score"])
                st.success(
                    f"Assessment Atlas generado: {score['overall_score']}/5 "
                    f"({score['interpretation']})."
                )
                st.rerun()

    with st.expander("Conector Microsoft Fabric · solo lectura", expanded=False):
        st.caption(
            "Reutiliza la identidad Entra delegada configurada en el entorno compartido. "
            "Solo permite metadata y consultas agregadas nombradas; no acepta SQL libre ni publica cambios."
        )
        filter_columns = st.columns(2)
        schema_name = filter_columns[0].text_input(
            "Schema exacto (opcional)", placeholder="Ejemplo: gold_sic",
            key=f"fabric-schema-{project_id}",
        )
        table_name_pattern = filter_columns[1].text_input(
            "Filtrar tablas/vistas por nombre (opcional)", placeholder="Ejemplo: fact_riesgo",
            key=f"fabric-table-pattern-{project_id}",
        )
        connection_column, discovery_column = st.columns(2)
        if connection_column.button("Comprobar conexión Fabric", key=f"fabric-check-{project_id}"):
            try:
                connection = service.check_fabric_connection()
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state[f"fabric-connection-{project_id}"] = connection
        connection = st.session_state.get(f"fabric-connection-{project_id}")
        if connection:
            st.success(
                f"Conexión de solo lectura confirmada: {connection['identity']} · "
                f"{connection['database']}"
            )
        query_labels = {
            "risk_summary": "Resumen de fact_riesgo",
            "risk_levels": "Distribución de niveles de riesgo",
            "impact_summary": "Resumen REAL / proxies / pendientes",
            "impact_statuses": "Estados REAL / DEFAULT",
        }
        query_column, query_button_column = st.columns([2, 1])
        query_name = query_column.selectbox(
            "Consulta agregada read-only",
            list(query_labels),
            format_func=query_labels.get,
            key=f"fabric-query-{project_id}",
        )
        if query_button_column.button("Ejecutar consulta real", key=f"fabric-query-run-{project_id}"):
            try:
                query_result = service.execute_fabric_validation_query(query_name)
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state[f"fabric-query-result-{project_id}"] = query_result
        query_result = st.session_state.get(f"fabric-query-result-{project_id}")
        if query_result:
            st.success(
                f"Consulta real confirmada: {query_result['query_name']} · "
                f"{query_result['operation']} · {len(query_result['rows'])} resultado(s)."
            )
            st.dataframe(query_result["rows"], width="stretch", hide_index=True)
        if discovery_column.button("Inventariar metadata Fabric", key=f"fabric-discover-{project_id}"):
            try:
                discovery = service.discover_fabric_metadata(
                    project_id, table_name_pattern, schema_name
                )
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state[f"fabric-discovery-{project_id}"] = discovery
        discovery = st.session_state.get(f"fabric-discovery-{project_id}")
        if discovery:
            st.success(
                f"Inventario guardado: {len(discovery['tables'])} tablas/vistas y "
                f"{len(discovery['columns'])} columnas."
            )
            st.caption(str(discovery["package_path"]))
            st.dataframe(discovery["tables"], width="stretch", hide_index=True)
            if st.button("Incorporar metadata al proyecto Atlas", key=f"fabric-import-{project_id}"):
                try:
                    imported = service.import_fabric_metadata(project_id, discovery)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Metadata incorporada: {imported['added']} objetos nuevos "
                        f"({imported['tables']} tablas/vistas y {imported['columns']} columnas)."
                    )
                    st.rerun()

    assessments = service.list_atlas_assessments(project_id)
    if not assessments:
        st.info("Todavia no hay assessments Atlas para este proyecto.")
        return

    latest = assessments[0]
    with st.expander("Ultimo assessment Atlas", expanded=True):
        scope = dict(latest.get("scope", {}))
        st.caption(
            f"Run: {latest.get('run_id')} · Cliente: {scope.get('client_id')} · "
            f"Dominio: {scope.get('domain_id')} · Data product: {scope.get('data_product_id')}"
        )
        st.caption(f"Paquete local: {latest.get('package_path')}")
        review = dict(latest.get("assessment_review", {}))
        if review:
            st.info(
                "Revision del baseline: "
                f"{review.get('status', 'pending_review')} Â· "
                "No equivale a aprobar una ontologia."
            )
            open_gaps = review.get("open_gap_ids", [])
            if open_gaps:
                st.caption(f"Gaps abiertos: {', '.join(str(gap) for gap in open_gaps)}")
            with st.form(f"atlas-review-{latest.get('run_id')}"):
                review_columns = st.columns(3)
                status_options = ["pending_review", "reviewed", "needs_follow_up"]
                current_status = str(review.get("status", "pending_review"))
                status = review_columns[0].selectbox(
                    "Decision de revision",
                    options=status_options,
                    index=status_options.index(current_status) if current_status in status_options else 0,
                )
                reviewer = review_columns[1].text_input("Revisor/a", value=str(review.get("reviewer", "")))
                reviewer_role = review_columns[2].text_input("Rol", value=str(review.get("reviewer_role", "")))
                note = st.text_area("Nota de revision", value=str(review.get("note", "")))
                if st.form_submit_button("Guardar revision Atlas"):
                    try:
                        service.update_atlas_review(
                            project_id,
                            str(latest["run_id"]),
                            status,
                            reviewer,
                            reviewer_role,
                            note,
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.success("Revision de baseline registrada.")
                        st.rerun()
    rows = [
        {
            "run_id": assessment.get("run_id"),
            "creado": assessment.get("created_at"),
            "cliente": dict(assessment.get("scope", {})).get("client_id"),
            "dominio": dict(assessment.get("scope", {})).get("domain_id"),
            "data_product": dict(assessment.get("scope", {})).get("data_product_id"),
        }
        for assessment in assessments
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def render_nexo_registry(project_id: str, project) -> None:
    st.subheader("Nexo Â· Registry & Validation")
    st.caption(
        "Convierte un assessment Atlas en candidatos revisables. Una release contiene solo "
        "candidatos aprobados y no puede emitirse con decisiones pendientes."
    )
    assessments = service.list_atlas_assessments(project_id)
    if not assessments:
        st.info("Genera primero un assessment Atlas para crear un draft Nexo.")
        return

    assessment_options = {str(item["run_id"]): item for item in assessments}
    with st.form(f"nexo-draft-{project_id}"):
        assessment_run_id = st.selectbox(
            "Assessment Atlas de origen",
            options=list(assessment_options.keys()),
            format_func=lambda item: (
                f"{item} Â· {dict(assessment_options[item].get('scope', {})).get('domain_id', 'sin-dominio')}"
            ),
        )
        source_authority = st.selectbox(
            "Autoridad de fuente",
            options=["technical", "documentation", "hybrid"],
            format_func=lambda item: {
                "technical": "Technical-first: Fabric define el universo técnico",
                "documentation": "Documentation-first: la documentación define el alcance",
                "hybrid": "Hybrid: combina documentación y metadata técnica",
            }[item],
        )
        if st.form_submit_button("Crear draft Nexo"):
            try:
                draft = service.create_nexo_draft(
                    project_id, assessment_run_id, source_authority=source_authority
                )
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
            else:
                st.success(f"Draft Nexo creado con {draft['manifest']['candidate_summary']['total']} candidatos.")
                st.rerun()

    drafts = service.list_nexo_drafts(project_id)
    if not drafts:
        st.caption("Todavia no hay drafts Nexo para este proyecto.")
        return

    draft_options = {str(item["draft_id"]): item for item in drafts}
    selected_draft_id = st.selectbox(
        "Draft Nexo",
        options=list(draft_options.keys()),
        format_func=lambda item: f"{item} Â· Atlas {draft_options[item]['source_assessment']['run_id']}",
    )
    draft = service.get_nexo_draft(project_id, selected_draft_id)
    summary = dict(draft["manifest"]["candidate_summary"])
    metrics = st.columns(4)
    metrics[0].metric("Candidatos", summary["total"])
    metrics[1].metric("Pendientes", summary["pending_review"])
    metrics[2].metric("Aprobados", summary["approved"])
    metrics[3].metric("Rechazados", summary["rejected"])

    candidates = list(draft["candidates"])
    model_elements = list(draft.get("model_elements", []))
    model_summary = dict(
        draft["manifest"].get(
            "model_element_summary",
            {"total": 0, "pending_review": 0, "approved": 0, "rejected": 0},
        )
    )
    with st.expander("Modelo canónico: propiedades, relaciones y gobierno", expanded=False):
        st.caption(
            "Estos elementos se agregan explícitamente, se vinculan a candidatos de Atlas y requieren "
            "una decisión humana antes de entrar en una release."
        )
        model_metrics = st.columns(4)
        model_metrics[0].metric("Elementos", model_summary["total"])
        model_metrics[1].metric("Pendientes", model_summary["pending_review"])
        model_metrics[2].metric("Aprobados", model_summary["approved"])
        model_metrics[3].metric("Rechazados", model_summary["rejected"])
        if st.button(
            "Proponer source bindings unicos",
            key=f"nexo-propose-bindings-{selected_draft_id}",
        ):
            try:
                proposal_result = service.propose_nexo_source_bindings(project_id, selected_draft_id)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Propuestas creadas: {proposal_result['created']}. "
                    f"Matches ambiguos omitidos: {proposal_result['skipped_ambiguous']}."
                )
                st.rerun()
        candidate_options_for_model = {
            str(candidate["candidate_id"]): candidate for candidate in candidates
        }
        with st.form(f"nexo-model-add-{selected_draft_id}"):
            element_columns = st.columns(2)
            element_type = element_columns[0].selectbox(
                "Tipo de elemento", ["property", "relationship", "synonym", "constraint", "source_binding"]
            )
            owner = element_columns[1].text_input("Responsable de negocio (opcional)")
            name = st.text_input("Nombre del elemento")
            definition = st.text_area("Definición o regla del elemento")
            linked_candidate_ids = st.multiselect(
                "Candidatos vinculados (dos para relación/source binding; uno para los demás)",
                options=list(candidate_options_for_model.keys()),
                format_func=lambda item: (
                    f"{candidate_options_for_model[item]['candidate_type']} · "
                    f"{candidate_options_for_model[item]['name']}"
                ),
            )
            if st.form_submit_button("Agregar al modelo para revisión"):
                try:
                    service.add_nexo_model_element(
                        project_id, selected_draft_id, element_type, name, definition,
                        owner, linked_candidate_ids,
                    )
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Elemento agregado como pendiente de revisión.")
                    st.rerun()
        if model_elements:
            st.dataframe(
                [
                    {
                        "id": element["element_id"],
                        "tipo": element["element_type"],
                        "nombre": element["name"],
                        "estado": element["status"],
                        "responsable": element.get("owner", ""),
                        "vínculos": ", ".join(element.get("linked_candidate_ids", [])),
                    }
                    for element in model_elements
                ],
                width="stretch",
                hide_index=True,
            )
            element_options = {str(element["element_id"]): element for element in model_elements}
            selected_element_id = st.selectbox(
                "Elemento canónico para revisar",
                options=list(element_options.keys()),
                format_func=lambda item: (
                    f"{element_options[item]['element_type']} · {element_options[item]['name']}"
                ),
                key=f"nexo-model-selection-{selected_draft_id}",
            )
            selected_element = element_options[selected_element_id]
            with st.form(f"nexo-model-review-{selected_draft_id}-{selected_element_id}"):
                review_columns = st.columns(3)
                element_statuses = ["pending_review", "approved", "rejected"]
                element_status = review_columns[0].selectbox(
                    "Decisión del elemento", element_statuses,
                    index=element_statuses.index(selected_element["status"]),
                )
                element_reviewer = review_columns[1].text_input("Revisor/a del elemento")
                element_role = review_columns[2].text_input("Rol del revisor/a")
                element_note = st.text_area("Nota de revisión del elemento")
                if st.form_submit_button("Guardar decisión del elemento"):
                    try:
                        service.update_nexo_model_element(
                            project_id, selected_draft_id, selected_element_id,
                            element_status, element_reviewer, element_role, element_note,
                        )
                    except (ValueError, FileNotFoundError) as exc:
                        st.error(str(exc))
                    else:
                        st.success("Decisión del elemento registrada.")
                        st.rerun()
        else:
            st.info("Todavía no hay elementos canónicos adicionales en este draft.")

    status_filter = st.selectbox(
        "Filtrar candidatos", ["all", "pending_review", "approved", "rejected"], key=f"nexo-filter-{selected_draft_id}"
    )
    visible_candidates = [
        candidate for candidate in candidates if status_filter == "all" or candidate["status"] == status_filter
    ]
    st.dataframe(
        [
            {
                "id": candidate["candidate_id"],
                "tipo": candidate["candidate_type"],
                "nombre": candidate["name"],
                "estado": candidate["status"],
                "confidence": candidate["confidence"],
                "evidencia": candidate["evidence"]["source_chunk_id"],
            }
            for candidate in visible_candidates
        ],
        width="stretch",
        hide_index=True,
    )
    if visible_candidates:
        candidate_options = {str(candidate["candidate_id"]): candidate for candidate in visible_candidates}
        selected_candidate_id = st.selectbox(
            "Candidato para revisar",
            options=list(candidate_options.keys()),
            format_func=lambda item: (
                f"{candidate_options[item]['candidate_type']} Â· {candidate_options[item]['name']}"
            ),
            key=f"nexo-candidate-{selected_draft_id}-{status_filter}",
        )
        selected_candidate = candidate_options[selected_candidate_id]
        with st.expander("Evidencia del candidato", expanded=False):
            st.caption(
                f"Documento: {selected_candidate['evidence']['source_document_id']} Â· "
                f"Chunk: {selected_candidate['evidence']['source_chunk_id']}"
            )
            st.code(selected_candidate["evidence"]["source_excerpt"], language="text")
        with st.form(f"nexo-review-{selected_draft_id}-{selected_candidate_id}"):
            review_columns = st.columns(3)
            status = review_columns[0].selectbox(
                "Decision", ["pending_review", "approved", "rejected"],
                index=["pending_review", "approved", "rejected"].index(selected_candidate["status"]),
            )
            reviewer = review_columns[1].text_input("Revisor/a")
            reviewer_role = review_columns[2].text_input("Rol")
            note = st.text_area("Motivo o nota")
            if st.form_submit_button("Guardar decision"):
                try:
                    service.update_nexo_candidate(
                        project_id, selected_draft_id, selected_candidate_id,
                        status, reviewer, reviewer_role, note,
                    )
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                        st.success("Decision registrada.")
                        st.rerun()

        with st.expander("Revision masiva de candidatos", expanded=False):
            bulk_options = {str(candidate["candidate_id"]): candidate for candidate in visible_candidates}
            with st.form(f"nexo-bulk-review-{selected_draft_id}-{status_filter}"):
                select_all_pending = st.checkbox(
                    "Seleccionar todos los candidatos pendientes visibles",
                    help="Incluye de una vez todos los candidatos pendientes del filtro actual.",
                )
                pending_bulk_ids = [
                    candidate_id
                    for candidate_id, candidate in bulk_options.items()
                    if candidate["status"] == "pending_review"
                ]
                if select_all_pending:
                    st.caption(f"Se aplicara la decision a {len(pending_bulk_ids)} candidatos pendientes.")
                selected_bulk_ids = st.multiselect(
                    "Candidatos seleccionados",
                    options=list(bulk_options.keys()),
                    format_func=lambda item: f"{bulk_options[item]['candidate_type']} · {bulk_options[item]['name']}",
                    disabled=select_all_pending,
                )
                bulk_columns = st.columns(3)
                bulk_status = bulk_columns[0].selectbox("Decision masiva", ["approved", "rejected"])
                bulk_reviewer = bulk_columns[1].text_input("Revisor/a masivo")
                bulk_role = bulk_columns[2].text_input("Rol masivo")
                bulk_note = st.text_area("Nota comun para la seleccion")
                if st.form_submit_button("Aplicar decision a seleccion"):
                    try:
                        result = service.bulk_update_nexo_candidates(
                            project_id, selected_draft_id,
                            pending_bulk_ids if select_all_pending else selected_bulk_ids,
                            bulk_status, bulk_reviewer, bulk_role, bulk_note,
                        )
                    except (ValueError, FileNotFoundError) as exc:
                        st.error(str(exc))
                    else:
                        st.success(f"Decision registrada en {result['updated']} candidatos.")
                        st.rerun()

    with st.expander("Sugerencias de consolidacion", expanded=False):
        st.caption(
            "Propone duplicados o casi duplicados para revisar. No fusiona, aprueba ni modifica candidatos."
        )
        if st.button("Generar sugerencias", key=f"nexo-consolidate-{selected_draft_id}"):
            try:
                suggestions = service.generate_nexo_consolidation_suggestions(project_id, selected_draft_id)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Sugerencias generadas: {len(suggestions['suggestions'])} "
                    f"({suggestions['mode']})."
                )
                st.rerun()
        consolidation = service.get_nexo_consolidation_suggestions(project_id, selected_draft_id)
        if consolidation:
            suggestions = list(consolidation["suggestions"])
            st.caption(
                f"Modo: {consolidation['mode']} Â· Sugerencias: {len(suggestions)} Â· "
                f"Candidatos analizados: {consolidation['candidate_count']}"
            )
            if consolidation.get("warning"):
                st.warning(str(consolidation["warning"]))
            if suggestions:
                suggestion_options = {str(item["suggestion_id"]): item for item in suggestions}
                selected_suggestion_id = st.selectbox(
                    "Grupo sugerido",
                    options=list(suggestion_options.keys()),
                    format_func=lambda item: (
                        f"{item}: {suggestion_options[item]['canonical_candidate_id']} + "
                        f"{len(suggestion_options[item]['duplicate_candidate_ids'])} candidatos"
                    ),
                    key=f"nexo-consolidation-selection-{selected_draft_id}",
                )
                selected_suggestion = suggestion_options[selected_suggestion_id]
                st.write(selected_suggestion["reason"])
                st.code(
                    "Canonical: " + str(selected_suggestion["canonical_candidate_id"]) + "\n" +
                    "Posibles duplicados: " + ", ".join(selected_suggestion["duplicate_candidate_ids"]),
                    language="text",
                )
                with st.form(f"nexo-consolidation-review-{selected_draft_id}-{selected_suggestion_id}"):
                    status_options = ["pending_review", "accepted_as_review_plan", "rejected"]
                    status = st.selectbox(
                        "Decision de consolidacion",
                        status_options,
                        index=status_options.index(selected_suggestion["status"]),
                    )
                    reviewer = st.text_input("Revisor/a de consolidacion")
                    note = st.text_area("Nota de consolidacion")
                    if st.form_submit_button("Guardar decision de consolidacion"):
                        try:
                            service.update_nexo_consolidation_suggestion(
                                project_id, selected_draft_id, selected_suggestion_id,
                                status, reviewer, note,
                            )
                        except (ValueError, FileNotFoundError) as exc:
                            st.error(str(exc))
                        else:
                            st.success("Decision de consolidacion registrada.")
                            st.rerun()
                if selected_suggestion["status"] == "accepted_as_review_plan":
                    with st.form(f"nexo-consolidation-apply-{selected_draft_id}-{selected_suggestion_id}"):
                        apply_reviewer = st.text_input("Revisor/a que aplica la consolidacion")
                        apply_note = st.text_area("Nota de aplicacion")
                        confirmed = st.checkbox(
                            "Entiendo que los duplicados pendientes quedaran rechazados; el canonico no sera aprobado automaticamente."
                        )
                        if st.form_submit_button("Aplicar consolidacion", disabled=not confirmed):
                            try:
                                result = service.apply_nexo_consolidation_suggestion(
                                    project_id, selected_draft_id, selected_suggestion_id,
                                    apply_reviewer, apply_note,
                                )
                            except (ValueError, FileNotFoundError) as exc:
                                st.error(str(exc))
                            else:
                                st.success(
                                    f"Consolidacion aplicada: {result['rejected_duplicates']} duplicados rechazados; "
                                    f"{result['canonical_candidate_id']} sigue sin aprobar automaticamente."
                                )
                                st.rerun()
            else:
                st.info("No se detectaron sugerencias de consolidacion.")

    with st.expander("Comparar impacto semántico", expanded=False):
        st.caption(
            "Compara por tipo y nombre normalizado. El resultado no modifica candidatos ni releases; "
            "sirve para revisar el impacto antes o después de publicar."
        )
        releases = service.list_nexo_releases(project_id)
        if not releases:
            st.info("Emite una primera release para poder comparar el draft contra una línea base.")
        else:
            release_options = {str(release["release_id"]): release for release in releases}
            with st.form(f"nexo-draft-diff-{selected_draft_id}"):
                baseline_release_id = st.selectbox(
                    "Release base para comparar con este draft",
                    options=list(release_options.keys()),
                    format_func=lambda item: f"{item} · {release_options[item]['created_at']}",
                )
                if st.form_submit_button("Comparar draft con release base"):
                    try:
                        comparison = service.compare_nexo_draft_to_release(
                            project_id, selected_draft_id, baseline_release_id
                        )
                    except (ValueError, FileNotFoundError) as exc:
                        st.error(str(exc))
                    else:
                        st.session_state[f"nexo-comparison-{project_id}"] = comparison
            if len(releases) > 1:
                with st.form(f"nexo-release-diff-{selected_draft_id}"):
                    comparison_columns = st.columns(2)
                    baseline_id = comparison_columns[0].selectbox(
                        "Release inicial", list(release_options.keys()),
                        key=f"nexo-release-diff-before-{selected_draft_id}",
                    )
                    candidate_id = comparison_columns[1].selectbox(
                        "Release final", list(release_options.keys()),
                        key=f"nexo-release-diff-after-{selected_draft_id}",
                    )
                    if st.form_submit_button("Comparar dos releases"):
                        try:
                            comparison = service.compare_nexo_releases(
                                project_id, baseline_id, candidate_id
                            )
                        except (ValueError, FileNotFoundError) as exc:
                            st.error(str(exc))
                        else:
                            st.session_state[f"nexo-comparison-{project_id}"] = comparison
        comparison = st.session_state.get(f"nexo-comparison-{project_id}")
        if comparison:
            comparison_summary = dict(comparison["summary"])
            comparison_metrics = st.columns(4)
            comparison_metrics[0].metric("Agregados", comparison_summary["added"])
            comparison_metrics[1].metric("Eliminados", comparison_summary["removed"])
            comparison_metrics[2].metric("Cambiados", comparison_summary["changed"])
            comparison_metrics[3].metric("Sin cambios", comparison_summary["unchanged"])
            st.caption(str(comparison["comparison_path"]))
            for label, key in (("Agregados", "added"), ("Eliminados", "removed"), ("Cambiados", "changed")):
                if comparison[key]:
                    st.write(label)
                    st.dataframe(comparison[key], width="stretch", hide_index=True)

    with st.expander("Preparar interoperabilidad", expanded=False):
        st.caption(
            "Genera un mapping local de una release para revisión. No usa credenciales, no incluye "
            "datos de negocio y no publica cambios en plataformas externas."
        )
        interoperability_releases = service.list_nexo_releases(project_id)
        if not interoperability_releases:
            st.info("Emite una release Nexo para preparar un paquete de interoperabilidad.")
        else:
            interoperability_options = {
                str(release["release_id"]): release for release in interoperability_releases
            }
            targets = service.interoperability_targets()
            with st.form(f"nexo-interoperability-{selected_draft_id}"):
                release_id = st.selectbox(
                    "Release de origen", list(interoperability_options.keys()),
                    format_func=lambda item: f"{item} · {interoperability_options[item]['created_at']}",
                )
                target = st.selectbox(
                    "Destino preparado", list(targets.keys()),
                    format_func=lambda item: targets[item]["label"],
                )
                prepared_by = st.text_input("Responsable del mapping")
                mapping_note = st.text_area("Nota de preparación")
                if st.form_submit_button("Generar paquete local"):
                    try:
                        package = service.prepare_interoperability_package(
                            project_id, release_id, target, prepared_by, mapping_note
                        )
                    except (ValueError, FileNotFoundError) as exc:
                        st.error(str(exc))
                    else:
                        st.session_state[f"nexo-interoperability-result-{project_id}"] = package
            package = st.session_state.get(f"nexo-interoperability-result-{project_id}")
            if package:
                mapping_manifest = dict(package["manifest"])
                st.success(
                    f"Paquete preparado para {mapping_manifest['target_label']} en {package['package_path']}"
                )
                st.caption("Estado: ready_for_review · Modo: local_mapping_only")
                st.dataframe(package["mapping"]["mappings"], width="stretch", hide_index=True)

    with st.expander("Emitir release inmutable", expanded=False):
        pending_items = summary["pending_review"] + model_summary["pending_review"]
        if pending_items:
            st.warning(f"Faltan {pending_items} decisiones. La release permanece bloqueada.")
        with st.form(f"nexo-release-{selected_draft_id}"):
            released_by = st.text_input("Responsable de la release")
            release_note = st.text_area("Nota de release")
            if st.form_submit_button("Emitir release Nexo", disabled=bool(pending_items)):
                try:
                    release = service.publish_nexo_release(
                        project_id, selected_draft_id, released_by, release_note
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Release creada localmente: {release['package_path']}")


def render_argos_runtime(project_id: str, project) -> None:
    st.subheader("Investigación de riesgos")
    st.caption(
        "Explora los riesgos del negocio con preguntas en lenguaje natural. "
        "Argos reúne datos, contexto y explicaciones en una misma conversación."
    )
    llm_settings = load_llm_settings()
    if llm_settings.enabled:
        st.success(f"OpenAI activo · {llm_settings.model}")
    else:
        st.warning(
            "OpenAI no está activo en esta ejecución. Argos está usando el modo de respaldo; "
            "las respuestas serán limitadas."
        )
    releases = service.list_nexo_releases(project_id)
    if not releases:
        st.info("La investigación todavía no está disponible: falta preparar el contexto del negocio.")
        return
    release_id = str(releases[0]["release_id"])
    conversation_key = f"argos-conversation-{project_id}"
    conversation = st.session_state.setdefault(conversation_key, [])
    starter_questions = [
        "¿Cuál es el riesgo de la regla 1 en el SIC 12?",
        "¿Cuántos riesgos hay y cómo se distribuyen por nivel?",
        "¿Qué riesgos deberían priorizarse y por qué?",
    ]
    st.markdown(f"### {project.name}")
    st.caption("Contexto de investigación activo. Escribe una pregunta o elige un punto de partida.")
    starter_columns = st.columns(3)
    for index, starter_question in enumerate(starter_questions):
        if starter_columns[index].button(
            starter_question,
            key=f"argos-starter-{project_id}-{index}",
            use_container_width=True,
        ):
            _run_argos_question(project_id, release_id, starter_question, conversation_key)
            st.rerun()
    with st.form(f"argos-chat-{project_id}", clear_on_submit=True):
        question = st.text_area(
            "Tu pregunta",
            placeholder="Ejemplo: ¿Por qué subió el riesgo y qué debería revisar primero?",
            height=90,
        )
        if st.form_submit_button("Consultar", use_container_width=True) and question.strip():
            try:
                result = service.investigate_release(project_id, release_id, question)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
            else:
                conversation.append({"question": question.strip(), "result": result})
                st.rerun()
    if conversation:
        st.divider()
        for exchange in reversed(conversation):
            result = exchange["result"]
            with st.container(border=True):
                st.caption("Tu pregunta")
                st.markdown(f"**{exchange['question']}**")
                st.success(str(result["answer"]) if result["manifest"]["status"] == "answered" else str(result["answer"]))
                interpretation = result.get("interpretation")
                if interpretation:
                    st.write(interpretation)
                _render_argos_result_views(result)
                suggested_questions = result.get("suggested_questions", [])
                if suggested_questions:
                    st.markdown("**Puedes seguir por aquí**")
                    for suggestion_index, suggested_question in enumerate(suggested_questions):
                        if st.button(
                            suggested_question,
                            key=f"argos-follow-up-{project_id}-{manifest_id(result)}-{suggestion_index}",
                            use_container_width=True,
                        ):
                            _run_argos_question(
                                project_id, release_id, suggested_question, conversation_key
                            )
                            st.rerun()
                with st.expander("Detalles para analistas", expanded=False):
                    _render_argos_traceability(result)

    with st.expander("Batería de evaluación de Argos", expanded=False):
        st.caption(
            "Define qué debe responder Argos y de qué debe abstenerse. Cada ejecución valida "
            "el estado esperado y, si corresponde, el elemento de evidencia recuperado."
        )
        evaluation_release_id = release_id
        cases_key = f"argos-evaluation-cases-{project_id}"
        if st.button("Preparar batería base", key=f"argos-evaluation-suggest-{project_id}"):
            try:
                suggested_cases = service.suggest_argos_evaluation_cases(project_id, evaluation_release_id)
            except FileNotFoundError as exc:
                st.error(str(exc))
            else:
                st.session_state[cases_key] = "\n".join(
                    f"{case['question']} | {case['expected_status']} | {case['expected_item_name']}"
                    for case in suggested_cases
                )
                st.rerun()
        cases_text = st.text_area(
            "Casos: pregunta | estado esperado (answered/abstained) | evidencia esperada opcional",
            key=cases_key,
            placeholder="¿Qué es Cliente Activo? | answered | Cliente Activo\n¿Qué planeta es más grande? | abstained |",
            height=180,
        )
        if st.button("Ejecutar batería", key=f"argos-evaluation-run-{project_id}"):
            cases = []
            invalid_lines = []
            for line_number, raw_line in enumerate(cases_text.splitlines(), start=1):
                if not raw_line.strip():
                    continue
                values = [value.strip() for value in raw_line.split("|", maxsplit=2)]
                if len(values) == 1 and values[0]:
                    cases.append(
                        {
                            "case_id": f"manual-{line_number:03d}",
                            "question": values[0],
                            "expected_status": "answered",
                            "expected_item_name": "",
                        }
                    )
                    continue
                if len(values) < 2:
                    invalid_lines.append(str(line_number))
                    continue
                cases.append(
                    {
                        "case_id": f"manual-{line_number:03d}",
                        "question": values[0],
                        "expected_status": values[1],
                        "expected_item_name": values[2] if len(values) > 2 else "",
                    }
                )
            if invalid_lines:
                st.error("Formato inválido en líneas: " + ", ".join(invalid_lines))
            else:
                try:
                    evaluation = service.evaluate_argos_release(project_id, evaluation_release_id, cases)
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                    st.session_state[f"argos-evaluation-result-{project_id}"] = evaluation
        evaluation = st.session_state.get(f"argos-evaluation-result-{project_id}")
        if evaluation:
            evaluation_summary = dict(evaluation["summary"])
            metrics = st.columns(3)
            metrics[0].metric("Casos", evaluation_summary["total"])
            metrics[1].metric("Correctos", evaluation_summary["passed"])
            metrics[2].metric("Fallidos", evaluation_summary["failed"])
            st.caption(f"Paquete de evaluación: {evaluation['package_path']}")
            st.dataframe(
                [
                    {
                        "pregunta": case["question"],
                        "esperado": case["expected_status"],
                        "obtenido": case["actual_status"],
                        "respuesta": case.get("investigation", {}).get("answer", ""),
                        "consulta": case.get("investigation", {}).get("live_query", {}).get("query_name", ""),
                        "evidencia": ", ".join(case["retrieved_item_names"]),
                        "correcto": case["passed"],
                        "motivo": case["failure_reason"],
                    }
                    for case in evaluation["cases"]
                ],
                width="stretch",
                hide_index=True,
            )
            for case in evaluation["cases"]:
                investigation = case.get("investigation", {})
                live_query = investigation.get("live_query", {})
                with st.expander(f"Resultado: {case['question']}", expanded=True):
                    st.write(investigation.get("answer", "Sin respuesta"))
                    if live_query:
                        st.caption(
                            f"Consulta Fabric: {live_query.get('query_name', 'consulta')} · "
                            f"{live_query.get('operation', 'SELECT')} · "
                            f"{len(live_query.get('rows', []))} fila(s)"
                        )
                        if live_query.get("rows"):
                            st.dataframe(live_query["rows"], width="stretch", hide_index=True)


def _run_argos_question(
    project_id: str, release_id: str, question: str, conversation_key: str
) -> None:
    try:
        result = service.investigate_release(project_id, release_id, question)
    except (ValueError, FileNotFoundError) as exc:
        st.error(str(exc))
        return
    st.session_state.setdefault(conversation_key, []).append(
        {"question": question, "result": result}
    )


def _render_argos_result_views(result: dict[str, object]) -> None:
    live_query = result.get("live_query")
    rows = [row for row in live_query.get("rows", []) if isinstance(row, dict)] if isinstance(live_query, dict) else []
    if rows:
        st.markdown("**Datos encontrados**")
        st.dataframe(rows, width="stretch", hide_index=True)
    if isinstance(live_query, dict) and live_query.get("query_name") == "risk_levels" and rows:
        chart_data = {
            str(row.get("riesgo_final_texto", "Sin nivel")): int(row.get("total_rows", 0))
            for row in rows
        }
        if chart_data:
            st.markdown("**Distribución de riesgos**")
            st.bar_chart(chart_data, height=220)
    visualization = result.get("visualization")
    if rows and isinstance(live_query, dict) and live_query.get("query_name") == "risk_rule_sic":
        row = rows[0]
        st.markdown("**Cómo se forma el resultado**")
        flow = st.columns(3)
        flow[0].metric("Probabilidad", str(row.get("probabilidad_final_texto", "Sin dato")))
        flow[1].metric("Impacto", str(row.get("impacto_final_texto", "Sin dato")))
        flow[2].metric("Riesgo final", str(row.get("riesgo_final_texto", "Sin dato")))
        st.caption(f"El resultado se obtiene aplicando el método {row.get('metodo_calculo', 'informado por la fuente')}.")
    elif isinstance(visualization, dict):
        st.markdown("**Explicación visual**")
        st.info("No hay datos suficientes para construir un gráfico de negocio con este resultado.")


def manifest_id(result: dict[str, object]) -> str:
    return str(dict(result.get("manifest", {})).get("investigation_id", "result"))


def _render_argos_traceability(result: dict[str, object]) -> None:
    manifest = dict(result.get("manifest", {}))
    st.caption(
        f"Estado: {manifest.get('status', 'desconocido')} · "
        f"Ejecución registrada en: {result.get('package_path', 'sin ruta')}"
    )
    reasoning_advisory = result.get("reasoning_advisory")
    if isinstance(reasoning_advisory, dict):
        st.caption(str(reasoning_advisory.get("message", "")))
        st.caption(
            f"Motor: {reasoning_advisory.get('model_used', 'sin informar')} · "
            f"Configuración: {reasoning_advisory.get('configured_provider', 'sin informar')} / "
            f"{reasoning_advisory.get('configured_model', 'sin informar')}"
        )
    live_query = result.get("live_query")
    if isinstance(live_query, dict):
        st.caption(
            f"Fuente: {live_query.get('query_name', 'consulta')} · "
            f"{live_query.get('operation', 'SELECT')} · "
            f"{len(live_query.get('rows', []))} resultado(s)"
        )
    retrieval = result.get("retrieval", [])
    if retrieval:
        st.dataframe(retrieval, width="stretch", hide_index=True)


def render_export_actions(project_id: str) -> None:
    st.subheader("Exportacion")
    json_payload = service.export_project_json(project_id)
    markdown_payload = service.export_project_markdown(project_id)
    st.download_button(
        "Descargar JSON",
        data=json_payload,
        file_name=f"{project_id}.json",
        mime="application/json",
        width="stretch",
    )
    st.download_button(
        "Descargar resumen Markdown",
        data=markdown_payload,
        file_name=f"{project_id}.md",
        mime="text/markdown",
        width="stretch",
    )


def render_snapshots(project_id: str) -> None:
    st.subheader("Snapshots locales")
    with st.form("create-snapshot", clear_on_submit=True):
        note = st.text_input("Nota del snapshot")
        submitted = st.form_submit_button("Crear snapshot")
        if submitted:
            service.create_snapshot(project_id, note=note)
            st.success("Snapshot generado")
            st.rerun()

    snapshots = service.list_snapshots(project_id)
    if not snapshots:
        st.caption("Todavia no hay snapshots para este proyecto.")
        return

    snapshot_options = {snapshot.snapshot_id: snapshot for snapshot in snapshots}
    selected_snapshot_id = st.selectbox(
        "Historial disponible",
        options=list(snapshot_options.keys()),
        format_func=lambda item: f"{item} | {snapshot_options[item].note or 'sin nota'}",
    )
    if st.button("Restaurar snapshot"):
        service.restore_snapshot(project_id, selected_snapshot_id)
        st.success("Snapshot restaurado")
        st.rerun()


def render_metadata_editor(project_id: str, metadata: dict[str, str]) -> None:
    with st.expander("Metadata del proyecto"):
        raw_metadata = "\n".join(f"{key}={value}" for key, value in metadata.items())
        with st.form("metadata-form"):
            metadata_blob = st.text_area(
                "Pares clave=valor, uno por linea",
                value=raw_metadata,
                height=140,
            )
            submitted = st.form_submit_button("Guardar metadata")
            if submitted:
                parsed: dict[str, str] = {}
                for line in metadata_blob.splitlines():
                    if not line.strip():
                        continue
                    key, separator, value = line.partition("=")
                    if not separator:
                        st.error(f"Linea invalida: {line}")
                        return
                    parsed[key.strip()] = value.strip()
                service.update_metadata(project_id, parsed)
                st.success("Metadata actualizada")
                st.rerun()


def render_project_editor(project) -> None:
    with st.expander("Editar proyecto"):
        with st.form("project-form"):
            project_name = st.text_input("Nombre del proyecto", value=project.name)
            project_description = st.text_area("Descripcion del proyecto", value=project.description)
            submitted = st.form_submit_button("Guardar datos del proyecto")
            if submitted:
                try:
                    service.update_project(project.id, project_name, project_description)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Proyecto actualizado")
                    st.rerun()


def render_bim_import(project_id: str, project) -> None:
    with st.expander("Importar model.bim", expanded=not project.concepts and not project.relations):
        st.caption(
            "Carga un modelo tabular .bim para poblar tablas, columnas, medidas y relaciones. "
            "El archivo original queda guardado localmente con hash para Atlas."
        )
        uploaded_file = st.file_uploader(
            "Archivo model.bim",
            type=["bim", "json"],
            key=f"bim-uploader-{project_id}",
        )
        clear_existing = st.checkbox(
            "Limpiar conceptos y relaciones actuales antes de importar",
            value=not project.concepts and not project.relations,
            key=f"bim-clear-{project_id}",
        )
        snapshot_note = st.text_input(
            "Nota para snapshot previo",
            value="before-bim-import",
            key=f"bim-note-{project_id}",
        )
        if uploaded_file is not None and st.button("Importar model.bim", key=f"bim-import-button-{project_id}"):
            try:
                _, summary = service.import_bim_file(
                    project_id,
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    clear_existing=clear_existing,
                    snapshot_note=snapshot_note,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(
                    "Importacion BIM lista: "
                    f"{summary['tables']} tablas, {summary['columns']} columnas, "
                    f"{summary['measures']} medidas y {summary['relationships']} relaciones detectadas."
                )
                st.rerun()


def render_tool2_context(project_id: str) -> None:
    st.subheader("Tool 2 · Business Context Scanner")
    settings = load_llm_settings()
    provider_label = (
        f"{settings.provider} · {settings.model} ({settings.configuration_source})"
        if settings.enabled
        else "disabled"
    )
    st.caption(
        "La app no puede usar tu sesion de Copilot como backend runtime. "
        f"Modo actual de extraccion: {provider_label}."
    )

    with st.expander("Configuracion LLM"):
        st.write("Variables de entorno soportadas:")
        st.code(
            "\n".join(
                [
                    "ONTO_LLM_PROVIDER=disabled | openai | azure_openai | ollama",
                    "ONTO_LLM_MODEL=gpt-4.1-mini | gpt-4o-mini | deployment-name | llama3.1:8b",
                    "ONTO_LLM_API_KEY=...",
                    "ONTO_LLM_BASE_URL=https://api.openai.com/v1  # o endpoint de Ollama",
                    "ONTO_AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com",
                    "ONTO_AZURE_OPENAI_DEPLOYMENT=<deployment>",
                    "ONTO_AZURE_OPENAI_API_VERSION=2024-10-21",
                ]
            ),
            language="bash",
        )
        st.caption("Sin proveedor configurado, el scanner usa heuristicas locales sin costo ni API key.")

    with st.expander("Cargar documentos", expanded=True):
        doc_type = st.selectbox("Tipo documental", options=SUPPORTED_DOCUMENT_TYPES)
        uploaded_files = st.file_uploader(
            "Archivos soportados",
            type=SUPPORTED_FILE_EXTENSIONS,
            accept_multiple_files=True,
            key=f"context-files-{project_id}",
        )
        if uploaded_files and st.button("Subir documentos", key=f"upload-docs-{project_id}"):
            loaded = 0
            for uploaded_file in uploaded_files:
                try:
                    service.upload_context_document(
                        project_id,
                        filename=uploaded_file.name,
                        content=uploaded_file.getvalue(),
                        doc_type=doc_type,
                        content_type=uploaded_file.type or "application/octet-stream",
                    )
                except ValueError as exc:
                    st.error(f"{uploaded_file.name}: {exc}")
                else:
                    loaded += 1
            if loaded:
                st.success(f"Se cargaron {loaded} documento(s).")
                st.rerun()

    documents = service.list_context_documents(project_id)
    if documents:
        integrity = service.get_context_document_integrity(project_id)
        duplicate_ids = dict(integrity["duplicate_document_ids"])
        if duplicate_ids:
            st.warning(
                "Se detectaron documentos heredados con IDs duplicados. "
                "El contexto actual puede no ser trazable hasta reparar y volver a analizar."
            )
            if st.button("Reparar IDs y reextraer documentos", key=f"repair-doc-ids-{project_id}"):
                summary = service.repair_context_document_ids(project_id)
                st.success(
                    f"Se repararon {summary['repaired']} documento(s). "
                    "Vuelve a ejecutar el analisis de contexto."
                )
                st.rerun()
        rows = [
            {
                "archivo": document.filename,
                "tipo": document.doc_type,
                "estado": document.extraction_status,
                "chars": document.extracted_chars,
                "subido": document.uploaded_at,
            }
            for document in documents
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
        if st.button("Analizar contexto de negocio", key=f"scan-context-{project_id}"):
            try:
                inventory = service.scan_business_context(project_id)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(
                    "Analisis listo: "
                    f"{len(inventory['business_terms'])} terminos, "
                    f"{len(inventory['definitions'])} definiciones, "
                    f"{len(inventory['business_rules'])} reglas y "
                    f"{len(inventory['questions_for_workshop'])} preguntas."
                )
                st.rerun()
    else:
        st.info("Todavia no hay documentos cargados para Tool 2.")

    inventory = service.get_business_context_inventory(project_id)
    if inventory:
        with st.expander("Resultado actual del scanner", expanded=True):
            metrics = st.columns(5)
            metrics[0].metric("Terminos", len(inventory.get("business_terms", [])))
            metrics[1].metric("Definiciones", len(inventory.get("definitions", [])))
            metrics[2].metric("Reglas", len(inventory.get("business_rules", [])))
            metrics[3].metric("KPIs", len(inventory.get("kpis", [])))
            metrics[4].metric("Preguntas", len(inventory.get("questions_for_workshop", [])))
            if inventory.get("scanner_warning"):
                st.warning(inventory["scanner_warning"])
            st.json(inventory)


def render_concepts(project_id: str, project) -> None:
    st.subheader("Conceptos")
    if project.concepts:
        rows = [
            {
                "id": concept.id,
                "nombre": concept.name,
                "estado": concept.status,
                "tags": ", ".join(concept.tags),
                "definicion": concept.definition,
            }
            for concept in project.concepts
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Todavia no hay conceptos cargados.")

    with st.form("add-concept", clear_on_submit=True):
        st.markdown("### Agregar concepto")
        name = st.text_input("Nombre del concepto")
        definition = st.text_area("Definicion")
        status = st.selectbox("Estado", options=["draft", "review", "approved"])
        tags = st.text_input("Tags separados por coma")
        submitted = st.form_submit_button("Guardar concepto")
        if submitted:
            try:
                service.add_concept(
                    project_id,
                    name=name,
                    definition=definition,
                    status=status,
                    tags=[item.strip() for item in tags.split(",") if item.strip()],
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Concepto guardado")
                st.rerun()

    if project.concepts:
        with st.expander("Editar o borrar concepto"):
            concept_options = {concept.id: concept for concept in project.concepts}
            selected_concept_id = st.selectbox(
                "Concepto",
                options=list(concept_options.keys()),
                format_func=lambda item: concept_options[item].name,
            )
            selected_concept = concept_options[selected_concept_id]
            with st.form("edit-concept"):
                name = st.text_input("Nombre", value=selected_concept.name)
                definition = st.text_area("Definicion", value=selected_concept.definition)
                status = st.selectbox(
                    "Estado",
                    options=["draft", "review", "approved"],
                    index=["draft", "review", "approved"].index(selected_concept.status)
                    if selected_concept.status in ["draft", "review", "approved"]
                    else 0,
                )
                tags = st.text_input("Tags separados por coma", value=", ".join(selected_concept.tags))
                save_submitted = st.form_submit_button("Guardar cambios")
                if save_submitted:
                    try:
                        service.update_concept(
                            project_id,
                            concept_id=selected_concept_id,
                            name=name,
                            definition=definition,
                            status=status,
                            tags=[item.strip() for item in tags.split(",") if item.strip()],
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.success("Concepto actualizado")
                        st.rerun()
            if st.button("Borrar concepto", type="secondary"):
                service.delete_concept(project_id, selected_concept_id)
                st.success("Concepto eliminado")
                st.rerun()


def render_relations(project_id: str, project) -> None:
    st.subheader("Relaciones")
    if project.relations:
        rows = [
            {
                "id": relation.id,
                "origen": relation.source_id,
                "tipo": relation.relation_type,
                "destino": relation.target_id,
                "descripcion": relation.description,
            }
            for relation in project.relations
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Todavia no hay relaciones cargadas.")

    if len(project.concepts) < 2:
        st.caption("Necesitas al menos dos conceptos para definir relaciones.")
        return

    concept_options = {concept.id: concept.name for concept in project.concepts}
    with st.form("add-relation", clear_on_submit=True):
        st.markdown("### Agregar relacion")
        source_id = st.selectbox(
            "Origen",
            options=list(concept_options.keys()),
            format_func=lambda item: concept_options[item],
            key="source_id",
        )
        target_id = st.selectbox(
            "Destino",
            options=list(concept_options.keys()),
            format_func=lambda item: concept_options[item],
            key="target_id",
        )
        relation_type = st.text_input("Tipo de relacion", value="depends-on")
        description = st.text_area("Descripcion")
        submitted = st.form_submit_button("Guardar relacion")
        if submitted:
            try:
                service.add_relation(
                    project_id,
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation_type,
                    description=description,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Relacion guardada")
                st.rerun()

    if project.relations:
        with st.expander("Editar o borrar relacion"):
            relation_options = {relation.id: relation for relation in project.relations}
            selected_relation_id = st.selectbox(
                "Relacion",
                options=list(relation_options.keys()),
                format_func=lambda item: f"{relation_options[item].source_id} --{relation_options[item].relation_type}--> {relation_options[item].target_id}",
            )
            selected_relation = relation_options[selected_relation_id]
            with st.form("edit-relation"):
                source_id = st.selectbox(
                    "Origen",
                    options=list(concept_options.keys()),
                    index=list(concept_options.keys()).index(selected_relation.source_id),
                    format_func=lambda item: concept_options[item],
                    key="edit_source_id",
                )
                target_id = st.selectbox(
                    "Destino",
                    options=list(concept_options.keys()),
                    index=list(concept_options.keys()).index(selected_relation.target_id),
                    format_func=lambda item: concept_options[item],
                    key="edit_target_id",
                )
                relation_type = st.text_input("Tipo de relacion", value=selected_relation.relation_type)
                description = st.text_area("Descripcion", value=selected_relation.description)
                save_submitted = st.form_submit_button("Guardar cambios de relacion")
                if save_submitted:
                    try:
                        service.update_relation(
                            project_id,
                            relation_id=selected_relation_id,
                            source_id=source_id,
                            target_id=target_id,
                            relation_type=relation_type,
                            description=description,
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.success("Relacion actualizada")
                        st.rerun()
            if st.button("Borrar relacion", type="secondary"):
                service.delete_relation(project_id, selected_relation_id)
                st.success("Relacion eliminada")
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="DataIA Ontology Workbench", layout="wide")

    render_create_project()
    selected_id = st.session_state.get("selected_project_id") or render_project_selector()
    if not selected_id:
        st.info("Crea un proyecto desde la barra lateral para empezar.")
        return

    project = service.get_project(selected_id)
    st.session_state["selected_project_id"] = project.id
    active_area = st.session_state.get("active_product_area", "Inicio")
    st.sidebar.divider()
    selected_area = st.sidebar.radio(
        "Navegacion",
        options=list(PRODUCT_AREAS.keys()),
        index=list(PRODUCT_AREAS.keys()).index(active_area) if active_area in PRODUCT_AREAS else 0,
        format_func=lambda item: PRODUCT_AREAS[item],
    )
    st.session_state["active_product_area"] = selected_area

    if selected_area == "Inicio":
        render_factory_home(project)
        return

    st.title("Investigación de riesgos" if selected_area == "Argos" else PRODUCT_AREAS[selected_area])
    if selected_area != "Argos":
        st.caption(f"Proyecto activo: {project.name} · Actualizado: {project.updated_at}")
    if selected_area == "Atlas":
        render_project_overview(project.id, project)
        render_atlas_assessment(project.id, project)
        st.divider()
        render_tool2_context(project.id)
    elif selected_area == "Nexo":
        render_nexo_registry(project.id, project)
    elif selected_area == "Argos":
        render_argos_runtime(project.id, project)
    else:
        render_project_overview(project.id, project)
        render_project_editor(project)
        render_bim_import(project.id, project)
        render_metadata_editor(project.id, project.metadata)
        left_column, right_column = st.columns((3, 2))
        with left_column:
            render_concepts(project.id, project)
        with right_column:
            render_relations(project.id, project)
        export_column, snapshot_column = st.columns((2, 2))
        with export_column:
            render_export_actions(project.id)
        with snapshot_column:
            render_snapshots(project.id)


if __name__ == "__main__":
    main()
