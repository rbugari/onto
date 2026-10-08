"""Nexo screen: review Atlas findings, build the canonical model and publish releases."""
from __future__ import annotations

import io
import zipfile

import streamlit as st

from onto_ui.i18n import LocalizedLabels, localize_rows, localized_tabs, option_labels, t

from ontology_workbench.platform_exports import COVERAGE_LABELS
from ontology_workbench.service import WorkbenchService
from onto_ui.common import require_reviewer, reviewer
from onto_ui.labels import DECISION_LABELS, short_timestamp

SOURCE_AUTHORITY_LABELS = LocalizedLabels({
    "technical": "Técnica primero: la metadata define el universo",
    "documentation": "Documentación primero: el negocio define el alcance",
    "hybrid": "Híbrida: combina documentación y metadata",
})
CANDIDATE_TYPE_LABELS = LocalizedLabels({
    "concept": "Concepto",
    "business_rule": "Regla",
    "kpi": "KPI",
    "technical_asset": "Activo técnico",
})
MODEL_ELEMENT_LABELS = LocalizedLabels({
    "property": "Propiedad",
    "relationship": "Relación",
    "synonym": "Sinónimo",
    "constraint": "Restricción",
    "source_binding": "Vínculo con fuente",
})
REVIEW_STATUSES = ["pending_review", "approved", "rejected"]
EMPTY_SUMMARY = {"total": 0, "pending_review": 0, "approved": 0, "rejected": 0}


def render_nexo(service: WorkbenchService, project_id: str) -> None:
    st.title(t("Nexo · Validar conocimiento"))
    st.caption(
        t("Convierte los hallazgos de Atlas en conocimiento aprobado y lo prepara para implementarlo en la "
        "ontología de Fabric, Databricks u otra plataforma del cliente. ONTO no la reemplaza: solo cubre lo que la "
        "plataforma no pueda (plan B).")
    )
    assessments = service.list_atlas_assessments(project_id)
    if not assessments:
        st.info(t("Generá primero un diagnóstico en Atlas para crear un draft."))
        return
    drafts = service.list_nexo_drafts(project_id)
    with st.expander(t("Crear draft desde un diagnóstico Atlas"), expanded=not drafts):
        _render_draft_creation(service, project_id, assessments)
    if not drafts:
        return

    draft_options = {str(item["draft_id"]): item for item in drafts}
    draft_id = st.selectbox(
        t("Draft en revisión"),
        list(draft_options),
        format_func=option_labels(list(draft_options), lambda item: _draft_label(draft_options[item])),
        key=f"nexo-draft-select-{project_id}",
    )
    draft = service.get_nexo_draft(project_id, draft_id)
    summary = dict(draft["manifest"]["candidate_summary"])
    model_summary = dict(draft["manifest"].get("model_element_summary", EMPTY_SUMMARY))
    pending = summary["pending_review"] + model_summary["pending_review"]
    _render_status(summary, model_summary, pending)

    review_tab, model_tab, consolidation_tab, compare_tab, release_tab = localized_tabs(
        ["Revisión de candidatos", "Modelo canónico", "Consolidación", "Comparar", "Release y entrega a la plataforma"],
        key=f"nexo-tabs-{project_id}",
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
        t('{v0} · {v1} · {v2} pendientes de {v3}', v0=short_timestamp(manifest.get('created_at')), v1=authority, v2=summary.get('pending_review', 0), v3=summary.get('total', 0))
    )


def _render_draft_creation(service: WorkbenchService, project_id: str, assessments) -> None:
    assessment_options = {str(item["run_id"]): item for item in assessments}
    with st.form(f"nexo-draft-{project_id}"):
        columns = st.columns(2)
        run_id = columns[0].selectbox(
            t("Diagnóstico Atlas de origen"),
            list(assessment_options),
            format_func=option_labels(list(assessment_options), lambda item: (
                t('{v0} · {v1}', v0=short_timestamp(assessment_options[item].get('created_at')), v1=dict(assessment_options[item].get('scope', {})).get('domain_id', 'sin dominio'))
            )),
        key='ui-nexo-_render_draft_creation-94')
        authority = columns[1].selectbox(
            t("Qué define el alcance"), list(SOURCE_AUTHORITY_LABELS), format_func=option_labels(list(SOURCE_AUTHORITY_LABELS), dict(SOURCE_AUTHORITY_LABELS).get)
        , key='ui-nexo-_render_draft_creation-102')
        if st.form_submit_button(t("Crear draft"), type="primary", key='ui-nexo-_render_draft_creation-105'):
            try:
                draft = service.create_nexo_draft(project_id, run_id, source_authority=authority)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
            else:
                st.session_state[f"nexo-draft-select-{project_id}"] = str(draft["manifest"]["draft_id"])
                st.rerun()


def _render_status(summary: dict[str, int], model_summary: dict[str, int], pending: int) -> None:
    metrics = st.columns(5)
    metrics[0].metric(t("Candidatos"), summary["total"])
    metrics[1].metric(t("Pendientes"), summary["pending_review"])
    metrics[2].metric(t("Aprobados"), summary["approved"])
    metrics[3].metric(t("Rechazados"), summary["rejected"])
    metrics[4].metric(t("Modelo canónico"), model_summary["total"], t('{v0} pendientes', v0=model_summary['pending_review']), delta_color="off")
    decided = summary["total"] + model_summary["total"] - pending
    total = summary["total"] + model_summary["total"]
    st.progress(decided / total if total else 1.0, text=t('{v0} de {v1} decisiones tomadas', v0=decided, v1=total))
    if pending:
        st.info(
            t('Siguiente paso: decidir {v0} elemento(s) pendiente(s). La release se habilita cuando no quede ninguno.', v0=pending),
            icon=":material/arrow_forward:",
        )
    else:
        st.success(t("Todo decidido. Podés emitir la release y prepararla para la plataforma en **Release y entrega a la plataforma**."))


# ---------------------------------------------------------------- Candidatos

def _render_candidate_review(service: WorkbenchService, project_id: str, draft_id: str, candidates) -> None:
    filter_columns = st.columns((2, 2, 3))
    status_filter = filter_columns[0].segmented_control(
        t("Estado"), ["pending_review", "approved", "rejected", "all"], format_func=option_labels(["pending_review", "approved", "rejected", "all"], dict(DECISION_LABELS).get),
        default="pending_review", key=f"nexo-status-filter-{draft_id}",
    ) or "all"
    types = sorted({str(item["candidate_type"]) for item in candidates})
    type_filter = filter_columns[1].multiselect(
        t("Tipo"), types, format_func=option_labels(types, lambda item: CANDIDATE_TYPE_LABELS.get(item, item)),
        key=f"nexo-type-filter-{draft_id}", placeholder=t("Todos"),
    )
    search = filter_columns[2].text_input(t("Buscar"), key=f"nexo-search-{draft_id}", placeholder=t("Nombre o definición"))
    visible = [
        item for item in candidates
        if (status_filter == "all" or item["status"] == status_filter)
        and (not type_filter or item["candidate_type"] in type_filter)
        and (not search or search.casefold() in t('{v0} {v1}', v0=item['name'], v1=item.get('definition', '')).casefold())
    ]
    if not visible:
        if status_filter == "pending_review":
            st.success(t("No quedan candidatos pendientes con este filtro."))
        else:
            st.info(t("Sin resultados."))
        return

    list_column, detail_column = st.columns((3, 2))
    with list_column:
        selection = st.dataframe(
            localize_rows([
                {
                    "Tipo": CANDIDATE_TYPE_LABELS.get(item["candidate_type"], item["candidate_type"]),
                    "Nombre": item["name"],
                    "Estado": DECISION_LABELS.get(item["status"], item["status"]),
                    "Confianza": item.get("confidence", 0),
                    "Sistema": item.get("source_id", ""),
                }
                for item in visible
            ]),
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
        t('{v0} · {v1} · confianza {v2}', v0=CANDIDATE_TYPE_LABELS.get(candidate['candidate_type'], candidate['candidate_type']), v1=DECISION_LABELS.get(candidate['status'], candidate['status']), v2=candidate.get('confidence', 0))
    )
    if candidate.get("definition"):
        st.write(candidate["definition"])
    evidence = dict(candidate.get("evidence", {}))
    if evidence.get("source_excerpt"):
        st.caption(t('Evidencia · {v0} · {v1}', v0=evidence.get('source_document_id', ''), v1=evidence.get('source_chunk_id', '')))
        st.code(str(evidence["source_excerpt"]), language="text", wrap_lines=True)
    decision = candidate.get("decision")
    if isinstance(decision, dict) and decision.get("reviewer"):
        st.caption(t('Última decisión: {v0} · {v1}', v0=decision.get('reviewer'), v1=decision.get('note', '')))
    note = st.text_input(t("Nota (opcional)"), key=f"nexo-note-{draft_id}-{candidate['candidate_id']}")
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
    with st.expander(t('Decisión masiva sobre {v0} pendiente(s) visibles', v0=len(pending_ids))):
        with st.form(f"nexo-bulk-{draft_id}"):
            bulk_status = st.segmented_control(
                t("Decisión"), ["approved", "rejected"], format_func=option_labels(["approved", "rejected"], dict(DECISION_LABELS).get), default="approved"
            , key='ui-nexo-_render_bulk_review-229')
            note = st.text_input(t("Nota común"), key='ui-nexo-_render_bulk_review-232')
            confirmed = st.checkbox(t("Confirmo que revisé la lista filtrada"), key='ui-nexo-_render_bulk_review-233')
            if st.form_submit_button(t("Aplicar"), key='ui-nexo-_render_bulk_review-234'):
                if not confirmed:
                    st.error(t("Confirmá la revisión antes de aplicar."))
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
        t("Propiedades, relaciones, sinónimos, restricciones y vínculos con las fuentes. "
        "Cada elemento requiere una decisión humana antes de entrar en la release.")
    )
    candidates = {str(item["candidate_id"]): item for item in draft["candidates"]}
    elements = list(draft.get("model_elements", []))
    if st.button(t("Proponer vínculos con fuentes (coincidencias únicas)"), key=f"nexo-propose-bindings-{draft_id}"):
        try:
            result = service.propose_nexo_source_bindings(project_id, draft_id)
        except (ValueError, FileNotFoundError) as exc:
            st.error(str(exc))
        else:
            st.toast(t('{v0} vínculos propuestos; {v1} ambiguos omitidos.', v0=result['created'], v1=result['skipped_ambiguous']))
            st.rerun()

    if elements:
        element_options = {str(item["element_id"]): item for item in elements}
        st.dataframe(
            localize_rows([
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
            ]),
            width="stretch",
            hide_index=True,
        )
        columns = st.columns((3, 2))
        element_id = columns[0].selectbox(
            t("Elemento a decidir"), list(element_options),
            format_func=option_labels(list(element_options), lambda item: t('{v0} · {v1}', v0=MODEL_ELEMENT_LABELS.get(element_options[item]['element_type'], ''), v1=element_options[item]['name'])),
            key=f"nexo-model-selection-{draft_id}",
        )
        status = columns[1].segmented_control(
            t("Decisión"), REVIEW_STATUSES, format_func=option_labels(REVIEW_STATUSES, dict(DECISION_LABELS).get),
            default=element_options[element_id]["status"], key=f"nexo-model-status-{draft_id}-{element_id}",
        )
        note = st.text_input(t("Nota"), key=f"nexo-model-note-{draft_id}-{element_id}")
        if st.button(t("Guardar decisión"), key=f"nexo-model-save-{draft_id}-{element_id}") and status:
            if status == "pending_review" or require_reviewer():
                name, role = reviewer()
                try:
                    service.update_nexo_model_element(project_id, draft_id, element_id, status, name, role, note)
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    else:
        st.info(t("Todavía no hay elementos en el modelo canónico."))

    with st.expander(t("Agregar elemento")):
        with st.form(f"nexo-model-add-{draft_id}", clear_on_submit=True):
            columns = st.columns(2)
            element_type = columns[0].selectbox(t("Tipo"), list(MODEL_ELEMENT_LABELS), format_func=option_labels(list(MODEL_ELEMENT_LABELS), dict(MODEL_ELEMENT_LABELS).get), key='ui-nexo-_render_model_elements-311')
            owner = columns[1].text_input(t("Responsable de negocio (opcional)"), key='ui-nexo-_render_model_elements-312')
            name = st.text_input(t("Nombre"), key='ui-nexo-_render_model_elements-313')
            definition = st.text_area(t("Definición o regla"), height=80, key='ui-nexo-_render_model_elements-314')
            linked = st.multiselect(
                t("Candidatos vinculados (dos para relación o vínculo con fuente; uno para los demás)"),
                list(candidates),
                format_func=option_labels(list(candidates), lambda item: t('{v0} · {v1}', v0=CANDIDATE_TYPE_LABELS.get(candidates[item]['candidate_type'], ''), v1=candidates[item]['name'])),
            key='ui-nexo-_render_model_elements-315')
            if st.form_submit_button(t("Agregar para revisión"), key='ui-nexo-_render_model_elements-320'):
                try:
                    service.add_nexo_model_element(project_id, draft_id, element_type, name, definition, owner, linked)
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()


# ---------------------------------------------------------------- Consolidación

def _render_consolidation(service: WorkbenchService, project_id: str, draft_id: str, candidates) -> None:
    st.caption(t("Detecta duplicados o casi duplicados. No fusiona ni aprueba nada por sí solo."))
    if st.button(t("Buscar duplicados"), key=f"nexo-consolidate-{draft_id}"):
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
        t('Modo: {v0} · {v1} grupo(s) · {v2} candidatos analizados', v0=consolidation['mode'], v1=len(suggestions), v2=consolidation['candidate_count'])
    )
    if consolidation.get("warning"):
        st.warning(str(consolidation["warning"]))
    if not suggestions:
        st.success(t("No se detectaron duplicados."))
        return
    names = {str(item["candidate_id"]): item["name"] for item in candidates}
    options = {str(item["suggestion_id"]): item for item in suggestions}
    suggestion_id = st.selectbox(
        t("Grupo"),
        list(options),
        format_func=option_labels(list(options), lambda item: (
            t('{v0} + {v1} · {v2}', v0=names.get(options[item]['canonical_candidate_id'], options[item]['canonical_candidate_id']), v1=len(options[item]['duplicate_candidate_ids']), v2=DECISION_LABELS.get(options[item]['status'], options[item]['status']))
        )),
        key=f"nexo-consolidation-selection-{draft_id}",
    )
    suggestion = options[suggestion_id]
    st.write(suggestion["reason"])
    st.markdown(
        t('**Canónico:** {v0}  \n**Posibles duplicados:** {v1}', v0=names.get(suggestion['canonical_candidate_id'], suggestion['canonical_candidate_id']), v1=', '.join(names.get(item, item) for item in suggestion['duplicate_candidate_ids']))
    )
    note = st.text_input(t("Nota"), key=f"nexo-consolidation-note-{draft_id}-{suggestion_id}")
    columns = st.columns(3)
    if columns[0].button(t("Aceptar como plan"), key=f"nexo-consolidation-accept-{suggestion_id}",
                         disabled=suggestion["status"] == "accepted_as_review_plan"):
        _decide_consolidation(service, project_id, draft_id, suggestion_id, "accepted_as_review_plan", note)
    if columns[1].button(t("Descartar"), key=f"nexo-consolidation-reject-{suggestion_id}",
                         disabled=suggestion["status"] == "rejected"):
        _decide_consolidation(service, project_id, draft_id, suggestion_id, "rejected", note)
    if suggestion["status"] == "accepted_as_review_plan":
        confirmed = columns[2].checkbox(
            t("Rechazar duplicados pendientes"), key=f"nexo-consolidation-confirm-{suggestion_id}",
            help=t("El canónico no se aprueba automáticamente."),
        )
        if columns[2].button(t("Aplicar"), type="primary", disabled=not confirmed, key=f"nexo-consolidation-apply-{suggestion_id}"):
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
    st.caption(t("Compara por tipo y nombre normalizado. No modifica candidatos ni releases."))
    releases = service.list_nexo_releases(project_id)
    if not releases:
        st.info(t("Emití una primera release para comparar contra una línea base."))
        return
    release_options = {str(item["release_id"]): item for item in releases}

    def label(item: str) -> str:
        return t('{v0} · {v1}', v0=short_timestamp(release_options[item].get('created_at')), v1=item)

    mode = st.segmented_control(
        t("Comparar"), ["draft", "releases"], default="draft", key=f"nexo-compare-mode-{draft_id}",
        format_func=option_labels(["draft", "releases"], {"draft": t("Este draft vs. una release"), "releases": t("Dos releases")}.get),
    ) or "draft"
    comparison_key = f"nexo-comparison-{project_id}"
    if mode == "draft":
        baseline = st.selectbox(t("Release base"), list(release_options), format_func=option_labels(list(release_options), label), key=f"nexo-diff-base-{draft_id}")
        if st.button(t("Comparar"), key=f"nexo-diff-run-{draft_id}"):
            try:
                st.session_state[comparison_key] = service.compare_nexo_draft_to_release(project_id, draft_id, baseline)
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
    elif len(releases) < 2:
        st.info(t("Hacen falta al menos dos releases."))
    else:
        columns = st.columns(2)
        before = columns[0].selectbox(t("Release inicial"), list(release_options), format_func=option_labels(list(release_options), label), index=1, key=f"nexo-diff-before-{draft_id}")
        after = columns[1].selectbox(t("Release final"), list(release_options), format_func=option_labels(list(release_options), label), key=f"nexo-diff-after-{draft_id}")
        if st.button(t("Comparar"), key=f"nexo-diff-releases-{draft_id}"):
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
            column.metric(t(text), summary[key])
        for text, key in (("Agregados", "added"), ("Eliminados", "removed"), ("Cambiados", "changed")):
            if comparison[key]:
                st.markdown(f"**{t(text)}**")
                st.dataframe(localize_rows(comparison[key]), width="stretch", hide_index=True)


# ---------------------------------------------------------------- Release

def _render_release(service: WorkbenchService, project_id: str, draft_id: str, pending: int) -> None:
    with st.container(border=True):
        st.markdown(t("**1. Emitir release**"))
        if pending:
            st.warning(t('Faltan {v0} decisiones; la release está bloqueada.', v0=pending))
        with st.form(f"nexo-release-{draft_id}"):
            columns = st.columns((1, 2))
            released_by = columns[0].text_input(t("Responsable de la release"), value=reviewer()[0], key='ui-nexo-_render_release-463')
            note = columns[1].text_input(t("Nota de release"), key='ui-nexo-_render_release-464')
            if st.form_submit_button(t("Emitir release"), type="primary", disabled=bool(pending), key='ui-nexo-_render_release-465'):
                try:
                    release = service.publish_nexo_release(project_id, draft_id, released_by, note)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(t('Release {v0} creada. Siguiente paso: prepararla para la plataforma destino.', v0=release['manifest']['release_id']))
        releases = service.list_nexo_releases(project_id)
        if releases:
            st.dataframe(
                localize_rows([
                    {"Release": item["release_id"], "Creada": short_timestamp(item.get("created_at")),
                     "Responsable": item.get("released_by", "")}
                    for item in releases
                ]),
                width="stretch",
                hide_index=True,
            )
    _render_delivery(service, project_id, draft_id)


def _render_delivery(service: WorkbenchService, project_id: str, draft_id: str) -> None:
    with st.container(border=True):
        st.markdown(t("**2. Entregar a la plataforma destino** (ruta preferida)"))
        st.caption(
            t("Genera archivos que la plataforma del cliente importa en su propia ontología: Fabric IQ (ítem Ontology y "
            "Data Agent) o Databricks (Pages, metric views, Unity Catalog y Genie). Indica qué se implementa ahí y "
            "qué queda en ONTO como plan B. No usa credenciales ni publica.")
        )
        releases = service.list_nexo_releases(project_id)
        if not releases:
            st.info(t("Emití una release para preparar un paquete."))
            return
        release_options = {str(item["release_id"]): item for item in releases}
        targets = service.interoperability_targets()
        target = st.segmented_control(
            t("Plataforma destino"), list(targets), format_func=option_labels(list(targets), lambda item: targets[item]["label"]),
            default="fabric", key=f"nexo-delivery-target-{draft_id}",
        ) or "fabric"
        with st.form(f"nexo-interoperability-{draft_id}-{target}"):
            columns = st.columns(2)
            release_id = columns[0].selectbox(
                "Release", list(release_options),
                format_func=option_labels(list(release_options), lambda item: t('{v0} · {v1}', v0=short_timestamp(release_options[item].get('created_at')), v1=item)),
            key='ui-nexo-_render_delivery-506')
            prepared_by = columns[1].text_input(t("Responsable del paquete"), value=reviewer()[0], key='ui-nexo-_render_delivery-510')
            settings_fields = dict(targets[target].get("settings", {}))
            setting_columns = st.columns(max(len(settings_fields), 1))
            settings = {
                key: column.text_input(t(label), key=f"nexo-delivery-{target}-{key}-{draft_id}")
                for column, (key, label) in zip(setting_columns, settings_fields.items())
            }
            note = st.text_input(t("Nota"), key='ui-nexo-_render_delivery-517')
            if st.form_submit_button(t("Generar paquete para la plataforma"), type="primary", key='ui-nexo-_render_delivery-518'):
                try:
                    st.session_state[f"nexo-interoperability-result-{project_id}"] = service.prepare_interoperability_package(
                        project_id, release_id, target, prepared_by, note, settings
                    )
                except (ValueError, FileNotFoundError) as exc:
                    st.error(str(exc))
        package = st.session_state.get(f"nexo-interoperability-result-{project_id}")
        if package and package.get("export"):
            _render_package(package)


def _render_package(package: dict[str, object]) -> None:
    export = dict(package["export"])
    summary = dict(export["summary"])
    counts = dict(summary["counts"])
    route_labels = {"A": t("A · Todo en la plataforma"), "B": t("B · Mixta (plataforma + ONTO)"), "C": t("C · Plan B en ONTO")}
    metrics = st.columns(4)
    metrics[0].metric(t("Ruta recomendada"), route_labels.get(str(summary["recommended_route"]), summary["recommended_route"]))
    metrics[1].metric(t("Implementables en la plataforma"), t('{v0} / {v1}', v0=summary['implementable_in_platform'], v1=summary['total']))
    metrics[2].metric(t("Falta completar"), counts.get("needs_completion", 0))
    metrics[3].metric(t("Fuera de alcance"), counts.get("outside_platform", 0))
    st.caption(str(summary["route_reason"]))
    st.download_button(
        t('Descargar paquete para {v0} (.zip)', v0=summary['target_label']),
        data=_zip_files(dict(export["files"])),
        file_name=f"onto-{summary['target']}-{package['manifest']['release_id']}.zip",
        mime="application/zip",
        key=f"nexo-download-{package['manifest']['package_id']}",
    )
    st.caption(t('También guardado en: {v0}', v0=package['package_path']))
    st.dataframe(
        localize_rows([
            {"Elemento": MODEL_ELEMENT_LABELS.get(item["element_type"], item["element_type"]), "Nombre": item["name"], "Resultado": t(COVERAGE_LABELS[item["status"]]),
             "Dónde queda": item["target_artifact"], "Acción": item["action"]}
            for item in export["coverage"]
        ]),
        width="stretch",
        hide_index=True,
        height=300,
    )


def _zip_files(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in sorted(files.items()):
            archive.writestr(path, content)
    return buffer.getvalue()
