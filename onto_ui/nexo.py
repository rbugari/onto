"""Nexo screen: review Atlas findings, build the canonical model and publish releases."""
from __future__ import annotations

import streamlit as st

from ontology_workbench.service import WorkbenchService
from onto_ui.common import require_reviewer, reviewer
from onto_ui.labels import DECISION_LABELS, short_timestamp

SOURCE_AUTHORITY_LABELS = {
    "technical": "Técnica primero: la metadata define el universo",
    "documentation": "Documentación primero: el negocio define el alcance",
    "hybrid": "Híbrida: combina documentación y metadata",
}
CANDIDATE_TYPE_LABELS = {
    "concept": "Concepto",
    "business_rule": "Regla",
    "kpi": "KPI",
    "technical_asset": "Activo técnico",
}
MODEL_ELEMENT_LABELS = {
    "property": "Propiedad",
    "relationship": "Relación",
    "synonym": "Sinónimo",
    "constraint": "Restricción",
    "source_binding": "Vínculo con fuente",
}
REVIEW_STATUSES = ["pending_review", "approved", "rejected"]
EMPTY_SUMMARY = {"total": 0, "pending_review": 0, "approved": 0, "rejected": 0}


def render_nexo(service: WorkbenchService, project_id: str) -> None:
    st.title("Nexo · Validar conocimiento")
    st.caption(
        "Convierte los hallazgos de Atlas en conocimiento aprobado y versionado. "
        "Argos solo usa releases aprobadas."
    )
    assessments = service.list_atlas_assessments(project_id)
    if not assessments:
        st.info("Generá primero un diagnóstico en Atlas para crear un draft.")
        return
    drafts = service.list_nexo_drafts(project_id)
    with st.expander("Crear draft desde un diagnóstico Atlas", expanded=not drafts):
        _render_draft_creation(service, project_id, assessments)
    if not drafts:
        return

    draft_options = {str(item["draft_id"]): item for item in drafts}
    draft_id = st.selectbox(
        "Draft en revisión",
        list(draft_options),
        format_func=lambda item: _draft_label(draft_options[item]),
        key=f"nexo-draft-select-{project_id}",
    )
    draft = service.get_nexo_draft(project_id, draft_id)
    summary = dict(draft["manifest"]["candidate_summary"])
    model_summary = dict(draft["manifest"].get("model_element_summary", EMPTY_SUMMARY))
    pending = summary["pending_review"] + model_summary["pending_review"]
    _render_status(summary, model_summary, pending)

    review_tab, model_tab, consolidation_tab, compare_tab, release_tab = st.tabs(
        ["Revisión de candidatos", "Modelo canónico", "Consolidación", "Comparar", "Release e interoperabilidad"]
    )
    with review_tab:
        _render_candidate_review(service, project_id, draft_id, list(draft["candidates"]))
    with model_tab:
        _render_model_elements(service, project_id, draft_id, draft, model_summary)
    with consolidation_tab:
        _render_consolidation(service, project_id, draft_id, list(draft["candidates"]))
    with compare_tab:
        _render_comparison(service, project_id, draft_id)
    with release_tab:
        _render_release(service, project_id, draft_id, pending)


def _draft_label(manifest: dict[str, object]) -> str:
    summary = dict(manifest.get("candidate_summary", EMPTY_SUMMARY))
    authority = str(manifest.get("source_authority", "technical"))
    return (
        f"{short_timestamp(manifest.get('created_at'))} · {authority} · "
        f"{summary.get('pending_review', 0)} pendientes de {summary.get('total', 0)}"
    )


def _render_draft_creation(service: WorkbenchService, project_id: str, assessments) -> None:
    assessment_options = {str(item["run_id"]): item for item in assessments}
    with st.form(f"nexo-draft-{project_id}"):
        columns = st.columns(2)
        run_id = columns[0].selectbox(
            "Diagnóstico Atlas de origen",
            list(assessment_options),
            format_func=lambda item: (
                f"{short_timestamp(assessment_options[item].get('created_at'))} · "
                f"{dict(assessment_options[item].get('scope', {})).get('domain_id', 'sin dominio')}"
            ),
        )
        authority = columns[1].selectbox(
            "Qué define el alcance", list(SOURCE_AUTHORITY_LABELS), format_func=SOURCE_AUTHORITY_LABELS.get
        )
        if st.form_submit_button("Crear draft", type="primary"):
            try:
                draft = service.create_nexo_draft(project_id, run_id, source_authority=authority)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
            else:
                st.session_state[f"nexo-draft-select-{project_id}"] = str(draft["manifest"]["draft_id"])
                st.rerun()


def _render_status(summary: dict[str, int], model_summary: dict[str, int], pending: int) -> None:
    metrics = st.columns(5)
    metrics[0].metric("Candidatos", summary["total"])
    metrics[1].metric("Pendientes", summary["pending_review"])
    metrics[2].metric("Aprobados", summary["approved"])
    metrics[3].metric("Rechazados", summary["rejected"])
    metrics[4].metric("Modelo canónico", model_summary["total"], f"{model_summary['pending_review']} pendientes", delta_color="off")
    decided = summary["total"] + model_summary["total"] - pending
    total = summary["total"] + model_summary["total"]
    st.progress(decided / total if total else 1.0, text=f"{decided} de {total} decisiones tomadas")
    if pending:
        st.info(
            f"Siguiente paso: decidir {pending} elemento(s) pendiente(s). La release se habilita cuando no quede ninguno.",
            icon=":material/arrow_forward:",
        )
    else:
        st.success("Todo decidido. Podés emitir la release en **Release e interoperabilidad**.")


# ---------------------------------------------------------------- Candidatos

def _render_candidate_review(service: WorkbenchService, project_id: str, draft_id: str, candidates) -> None:
    filter_columns = st.columns((2, 2, 3))
    status_filter = filter_columns[0].segmented_control(
        "Estado", ["pending_review", "approved", "rejected", "all"], format_func=DECISION_LABELS.get,
        default="pending_review", key=f"nexo-status-filter-{draft_id}",
    ) or "all"
    types = sorted({str(item["candidate_type"]) for item in candidates})
    type_filter = filter_columns[1].multiselect(
        "Tipo", types, format_func=lambda item: CANDIDATE_TYPE_LABELS.get(item, item),
        key=f"nexo-type-filter-{draft_id}", placeholder="Todos",
    )
    search = filter_columns[2].text_input("Buscar", key=f"nexo-search-{draft_id}", placeholder="Nombre o definición")
    visible = [
        item for item in candidates
        if (status_filter == "all" or item["status"] == status_filter)
        and (not type_filter or item["candidate_type"] in type_filter)
        and (not search or search.casefold() in f"{item['name']} {item.get('definition', '')}".casefold())
    ]
    if not visible:
        if status_filter == "pending_review":
            st.success("No quedan candidatos pendientes con este filtro.")
        else:
            st.info("Sin resultados.")
        return

    list_column, detail_column = st.columns((3, 2))
    with list_column:
        selection = st.dataframe(
            [
                {
                    "Tipo": CANDIDATE_TYPE_LABELS.get(item["candidate_type"], item["candidate_type"]),
                    "Nombre": item["name"],
                    "Estado": DECISION_LABELS.get(item["status"], item["status"]),
                    "Confianza": item.get("confidence", 0),
                    "Sistema": item.get("source_id", ""),
                }
                for item in visible
            ],
            width="stretch",
            hide_index=True,
            height=420,
            on_select="rerun",
            selection_mode="single-row",
            key=f"nexo-candidates-table-{draft_id}-{status_filter}",
            column_config={"Confianza": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")},
        )
        rows = list(selection.selection.rows) if selection else []
        _render_bulk_review(service, project_id, draft_id, visible)
    selected = visible[rows[0]] if rows and rows[0] < len(visible) else visible[0]
    with detail_column, st.container(border=True):
        _render_candidate_detail(service, project_id, draft_id, selected)


def _render_candidate_detail(service: WorkbenchService, project_id: str, draft_id: str, candidate) -> None:
    st.markdown(f"**{candidate['name']}**")
    st.caption(
        f"{CANDIDATE_TYPE_LABELS.get(candidate['candidate_type'], candidate['candidate_type'])} · "
        f"{DECISION_LABELS.get(candidate['status'], candidate['status'])} · confianza {candidate.get('confidence', 0)}"
    )
    if candidate.get("definition"):
        st.write(candidate["definition"])
    evidence = dict(candidate.get("evidence", {}))
    if evidence.get("source_excerpt"):
        st.caption(f"Evidencia · {evidence.get('source_document_id', '')} · {evidence.get('source_chunk_id', '')}")
        st.code(str(evidence["source_excerpt"]), language="text", wrap_lines=True)
    decision = candidate.get("decision")
    if isinstance(decision, dict) and decision.get("reviewer"):
        st.caption(f"Última decisión: {decision.get('reviewer')} · {decision.get('note', '')}")
    note = st.text_input("Nota (opcional)", key=f"nexo-note-{draft_id}-{candidate['candidate_id']}")
    buttons = st.columns(3)
    for column, (status, label, kind) in zip(
        buttons,
        (("approved", "Aprobar", "primary"), ("rejected", "Rechazar", "secondary"), ("pending_review", "Pendiente", "tertiary")),
    ):
        if column.button(label, type=kind, width="stretch", key=f"nexo-decide-{status}-{draft_id}-{candidate['candidate_id']}",
                         disabled=candidate["status"] == status):
            if status != "pending_review" and not require_reviewer():
                return
            name, role = reviewer()
            try:
                service.update_nexo_candidate(project_id, draft_id, str(candidate["candidate_id"]), status, name, role, note)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
            else:
                st.rerun()


def _render_bulk_review(service: WorkbenchService, project_id: str, draft_id: str, visible) -> None:
    pending_ids = [str(item["candidate_id"]) for item in visible if item["status"] == "pending_review"]
    if not pending_ids:
        return
    with st.expander(f"Decisión masiva sobre {len(pending_ids)} pendiente(s) visibles"):
        with st.form(f"nexo-bulk-{draft_id}"):
            bulk_status = st.segmented_control(
                "Decisión", ["approved", "rejected"], format_func=DECISION_LABELS.get, default="approved"
            )
            note = st.text_input("Nota común")
            confirmed = st.checkbox("Confirmo que revisé la lista filtrada")
            if st.form_submit_button("Aplicar"):
                if not confirmed:
                    st.error("Confirmá la revisión antes de aplicar.")
                elif require_reviewer():
                    name, role = reviewer()
                    try:
                        service.bulk_update_nexo_candidates(
                            project_id, draft_id, pending_ids, bulk_status or "approved", name, role, note
                        )
                    except (ValueError, FileNotFoundError) as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()


# ---------------------------------------------------------------- Modelo canónico

def _render_model_elements(service: WorkbenchService, project_id: str, draft_id: str, draft, model_summary) -> None:
    st.caption(
        "Propiedades, relaciones, sinónimos, restricciones y vínculos con las fuentes. "
        "Cada elemento requiere una decisión humana antes de entrar en la release."
    )
    candidates = {str(item["candidate_id"]): item for item in draft["candidates"]}
    elements = list(draft.get("model_elements", []))
    if st.button("Proponer vínculos con fuentes (coincidencias únicas)", key=f"nexo-propose-bindings-{draft_id}"):
        try:
            result = service.propose_nexo_source_bindings(project_id, draft_id)
        except (ValueError, FileNotFoundError) as exc:
            st.error(str(exc))
        else:
            st.toast(f"{result['created']} vínculos propuestos; {result['skipped_ambiguous']} ambiguos omitidos.")
            st.rerun()

    if elements:
        element_options = {str(item["element_id"]): item for item in elements}
        st.dataframe(
            [
                {
                    "Tipo": MODEL_ELEMENT_LABELS.get(item["element_type"], item["element_type"]),
                    "Nombre": item["name"],
                    "Estado": DECISION_LABELS.get(item["status"], item["status"]),
                    "Responsable": item.get("owner", ""),
                    "Vínculos": ", ".join(
                        str(candidates.get(link, {}).get("name", link)) for link in item.get("linked_candidate_ids", [])
                    ),
                }
                for item in elements
            ],
            width="stretch",
            hide_index=True,
        )
        columns = st.columns((3, 2))
        element_id = columns[0].selectbox(
            "Elemento a decidir", list(element_options),
            format_func=lambda item: f"{MODEL_ELEMENT_LABELS.get(element_options[item]['element_type'], '')} · {element_options[item]['name']}",
            key=f"nexo-model-selection-{draft_id}",
        )
        status = columns[1].segmented_control(
            "Decisión", REVIEW_STATUSES, format_func=DECISION_LABELS.get,
            default=element_options[element_id]["status"], key=f"nexo-model-status-{draft_id}-{element_id}",
        )
        note = st.text_input("Nota", key=f"nexo-model-note-{draft_id}-{element_id}")
        if st.button("Guardar decisión", key=f"nexo-model-save-{draft_id}-{element_id}") and status:
            if status == "pending_review" or require_reviewer():
                name, role = reviewer()
                try:
                    service.update_nexo_model_element(project_id, draft_id, element_id, status, name, role, note)
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    else:
        st.info("Todavía no hay elementos en el modelo canónico.")

    with st.expander("Agregar elemento"):
        with st.form(f"nexo-model-add-{draft_id}", clear_on_submit=True):
            columns = st.columns(2)
            element_type = columns[0].selectbox("Tipo", list(MODEL_ELEMENT_LABELS), format_func=MODEL_ELEMENT_LABELS.get)
            owner = columns[1].text_input("Responsable de negocio (opcional)")
            name = st.text_input("Nombre")
            definition = st.text_area("Definición o regla", height=80)
            linked = st.multiselect(
                "Candidatos vinculados (dos para relación o vínculo con fuente; uno para los demás)",
                list(candidates),
                format_func=lambda item: f"{CANDIDATE_TYPE_LABELS.get(candidates[item]['candidate_type'], '')} · {candidates[item]['name']}",
            )
            if st.form_submit_button("Agregar para revisión"):
                try:
                    service.add_nexo_model_element(project_id, draft_id, element_type, name, definition, owner, linked)
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()


# ---------------------------------------------------------------- Consolidación

def _render_consolidation(service: WorkbenchService, project_id: str, draft_id: str, candidates) -> None:
    st.caption("Detecta duplicados o casi duplicados. No fusiona ni aprueba nada por sí solo.")
    if st.button("Buscar duplicados", key=f"nexo-consolidate-{draft_id}"):
        try:
            service.generate_nexo_consolidation_suggestions(project_id, draft_id)
        except (ValueError, FileNotFoundError) as exc:
            st.error(str(exc))
        else:
            st.rerun()
    consolidation = service.get_nexo_consolidation_suggestions(project_id, draft_id)
    if not consolidation:
        return
    suggestions = list(consolidation["suggestions"])
    st.caption(
        f"Modo: {consolidation['mode']} · {len(suggestions)} grupo(s) · "
        f"{consolidation['candidate_count']} candidatos analizados"
    )
    if consolidation.get("warning"):
        st.warning(str(consolidation["warning"]))
    if not suggestions:
        st.success("No se detectaron duplicados.")
        return
    names = {str(item["candidate_id"]): item["name"] for item in candidates}
    options = {str(item["suggestion_id"]): item for item in suggestions}
    suggestion_id = st.selectbox(
        "Grupo",
        list(options),
        format_func=lambda item: (
            f"{names.get(options[item]['canonical_candidate_id'], options[item]['canonical_candidate_id'])} "
            f"+ {len(options[item]['duplicate_candidate_ids'])} · {DECISION_LABELS.get(options[item]['status'], options[item]['status'])}"
        ),
        key=f"nexo-consolidation-selection-{draft_id}",
    )
    suggestion = options[suggestion_id]
    st.write(suggestion["reason"])
    st.markdown(
        f"**Canónico:** {names.get(suggestion['canonical_candidate_id'], suggestion['canonical_candidate_id'])}  \n"
        f"**Posibles duplicados:** {', '.join(names.get(item, item) for item in suggestion['duplicate_candidate_ids'])}"
    )
    note = st.text_input("Nota", key=f"nexo-consolidation-note-{draft_id}-{suggestion_id}")
    columns = st.columns(3)
    if columns[0].button("Aceptar como plan", key=f"nexo-consolidation-accept-{suggestion_id}",
                         disabled=suggestion["status"] == "accepted_as_review_plan"):
        _decide_consolidation(service, project_id, draft_id, suggestion_id, "accepted_as_review_plan", note)
    if columns[1].button("Descartar", key=f"nexo-consolidation-reject-{suggestion_id}",
                         disabled=suggestion["status"] == "rejected"):
        _decide_consolidation(service, project_id, draft_id, suggestion_id, "rejected", note)
    if suggestion["status"] == "accepted_as_review_plan":
        confirmed = columns[2].checkbox(
            "Rechazar duplicados pendientes", key=f"nexo-consolidation-confirm-{suggestion_id}",
            help="El canónico no se aprueba automáticamente.",
        )
        if columns[2].button("Aplicar", type="primary", disabled=not confirmed, key=f"nexo-consolidation-apply-{suggestion_id}"):
            if require_reviewer():
                try:
                    service.apply_nexo_consolidation_suggestion(project_id, draft_id, suggestion_id, reviewer()[0], note)
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()


def _decide_consolidation(service, project_id: str, draft_id: str, suggestion_id: str, status: str, note: str) -> None:
    if not require_reviewer():
        return
    try:
        service.update_nexo_consolidation_suggestion(project_id, draft_id, suggestion_id, status, reviewer()[0], note)
    except (ValueError, FileNotFoundError) as exc:
        st.error(str(exc))
    else:
        st.rerun()


# ---------------------------------------------------------------- Comparar

def _render_comparison(service: WorkbenchService, project_id: str, draft_id: str) -> None:
    st.caption("Compara por tipo y nombre normalizado. No modifica candidatos ni releases.")
    releases = service.list_nexo_releases(project_id)
    if not releases:
        st.info("Emití una primera release para comparar contra una línea base.")
        return
    release_options = {str(item["release_id"]): item for item in releases}

    def label(item: str) -> str:
        return f"{short_timestamp(release_options[item].get('created_at'))} · {item}"

    mode = st.segmented_control(
        "Comparar", ["draft", "releases"], default="draft", key=f"nexo-compare-mode-{draft_id}",
        format_func={"draft": "Este draft vs. una release", "releases": "Dos releases"}.get,
    ) or "draft"
    comparison_key = f"nexo-comparison-{project_id}"
    if mode == "draft":
        baseline = st.selectbox("Release base", list(release_options), format_func=label, key=f"nexo-diff-base-{draft_id}")
        if st.button("Comparar", key=f"nexo-diff-run-{draft_id}"):
            try:
                st.session_state[comparison_key] = service.compare_nexo_draft_to_release(project_id, draft_id, baseline)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
    elif len(releases) < 2:
        st.info("Hacen falta al menos dos releases.")
    else:
        columns = st.columns(2)
        before = columns[0].selectbox("Release inicial", list(release_options), format_func=label, index=1, key=f"nexo-diff-before-{draft_id}")
        after = columns[1].selectbox("Release final", list(release_options), format_func=label, key=f"nexo-diff-after-{draft_id}")
        if st.button("Comparar", key=f"nexo-diff-releases-{draft_id}"):
            try:
                st.session_state[comparison_key] = service.compare_nexo_releases(project_id, before, after)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
    comparison = st.session_state.get(comparison_key)
    if comparison:
        summary = dict(comparison["summary"])
        metrics = st.columns(4)
        for column, (text, key) in zip(
            metrics, (("Agregados", "added"), ("Eliminados", "removed"), ("Cambiados", "changed"), ("Sin cambios", "unchanged"))
        ):
            column.metric(text, summary[key])
        for text, key in (("Agregados", "added"), ("Eliminados", "removed"), ("Cambiados", "changed")):
            if comparison[key]:
                st.markdown(f"**{text}**")
                st.dataframe(comparison[key], width="stretch", hide_index=True)


# ---------------------------------------------------------------- Release

def _render_release(service: WorkbenchService, project_id: str, draft_id: str, pending: int) -> None:
    release_column, interop_column = st.columns(2)
    with release_column, st.container(border=True):
        st.markdown("**Emitir release**")
        if pending:
            st.warning(f"Faltan {pending} decisiones; la release está bloqueada.")
        with st.form(f"nexo-release-{draft_id}"):
            released_by = st.text_input("Responsable de la release", value=reviewer()[0])
            note = st.text_area("Nota de release", height=80)
            if st.form_submit_button("Emitir release", type="primary", disabled=bool(pending)):
                try:
                    release = service.publish_nexo_release(project_id, draft_id, released_by, note)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Release {release['manifest']['release_id']} creada. Argos ya puede usarla.")
        releases = service.list_nexo_releases(project_id)
        if releases:
            st.dataframe(
                [
                    {"Release": item["release_id"], "Creada": short_timestamp(item.get("created_at")),
                     "Responsable": item.get("released_by", "")}
                    for item in releases
                ],
                width="stretch",
                hide_index=True,
            )
    with interop_column, st.container(border=True):
        st.markdown("**Preparar interoperabilidad**")
        st.caption("Genera un mapping local para Fabric, Databricks u otros destinos. No usa credenciales ni publica.")
        releases = service.list_nexo_releases(project_id)
        if not releases:
            st.info("Emití una release para preparar un paquete.")
            return
        release_options = {str(item["release_id"]): item for item in releases}
        targets = service.interoperability_targets()
        with st.form(f"nexo-interoperability-{draft_id}"):
            release_id = st.selectbox(
                "Release", list(release_options),
                format_func=lambda item: f"{short_timestamp(release_options[item].get('created_at'))} · {item}",
            )
            target = st.selectbox("Destino", list(targets), format_func=lambda item: targets[item]["label"])
            prepared_by = st.text_input("Responsable del mapping", value=reviewer()[0])
            note = st.text_area("Nota", height=70)
            if st.form_submit_button("Generar paquete local"):
                try:
                    st.session_state[f"nexo-interoperability-result-{project_id}"] = service.prepare_interoperability_package(
                        project_id, release_id, target, prepared_by, note
                    )
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
        package = st.session_state.get(f"nexo-interoperability-result-{project_id}")
        if package:
            st.success(f"Paquete para {package['manifest']['target_label']} listo para revisión.")
            st.caption(str(package["package_path"]))
            st.dataframe(package["mapping"]["mappings"], width="stretch", hide_index=True, height=250)
