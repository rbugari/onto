"""Argos screen: business conversation over the approved release, plus an analyst workspace."""
from __future__ import annotations

import json

import streamlit as st

from onto_ui.i18n import LocalizedLabels, localize_rows, localized_tabs, option_labels, t

from ontology_workbench.context_scanner import load_llm_settings
from ontology_workbench.result_views import infer_visualization, starter_questions
from ontology_workbench.runtime_evaluation import parse_evaluation_cases
from ontology_workbench.service import WorkbenchService
from onto_ui.labels import short_timestamp

STATUS_LABELS = LocalizedLabels({"answered": "Respondida", "abstained": "Abstención", "error": "Error"})


def render_argos(service: WorkbenchService, project_id: str) -> None:
    st.title(t("Argos · Investigación de negocio"))
    releases = service.list_nexo_releases(project_id)
    if not releases:
        st.info(t("Argos todavía no está disponible: falta emitir una release aprobada en Nexo."))
        return
    release_id = str(releases[0]["release_id"])
    settings = load_llm_settings()
    engine = t('{v0} · {v1}', v0=settings.provider, v1=settings.model) if settings.enabled else t("modo local determinista")
    st.caption(
        t('Banco de prueba del conocimiento aprobado antes de implementarlo en la plataforma del cliente, y runtime de plan B para lo que la plataforma no pueda cubrir. Responde solo con la release del {v0} y consultas autorizadas. Motor: {v1}.', v0=short_timestamp(releases[0].get('created_at')), v1=engine)
    )
    catalog = service.get_argos_query_catalog(project_id, release_id)
    chat_tab, analyst_tab = localized_tabs(["Conversación", "Analistas"], key=f"argos-tabs-{project_id}")
    with chat_tab:
        _render_conversation(service, project_id, release_id, catalog)
    with analyst_tab:
        _render_analyst_workspace(service, project_id, release_id, catalog)


# ---------------------------------------------------------------- Conversación

def _conversation(service: WorkbenchService, project_id: str, release_id: str) -> list[dict[str, object]]:
    key = f"argos-conversation-{project_id}"
    loaded_key = f"argos-history-loaded-{project_id}-{release_id}"
    conversation = st.session_state.setdefault(key, [])
    if not st.session_state.get(loaded_key):
        st.session_state[loaded_key] = True
        history = []
        for manifest in reversed(service.list_runtime_investigations(project_id, release_id)[:20]):
            investigation_id = str(manifest.get("investigation_id", ""))
            if not investigation_id:
                continue
            try:
                result = service.load_runtime_investigation(project_id, release_id, investigation_id)
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            history.append({"question": str(dict(result.get("request", {})).get("question", "")), "result": result})
        conversation[:0] = history
    return conversation


def _ask(service: WorkbenchService, project_id: str, release_id: str, question: str) -> None:
    try:
        with st.spinner(t("Argos está consultando el contexto y los datos permitidos…")):
            result = service.investigate_release(project_id, release_id, question)
    except (ValueError, FileNotFoundError) as exc:
        st.error(str(exc))
        return
    st.session_state.setdefault(f"argos-conversation-{project_id}", []).append(
        {"question": question.strip(), "result": result}
    )
    st.rerun()


def _render_conversation(service: WorkbenchService, project_id: str, release_id: str, catalog) -> None:
    conversation = _conversation(service, project_id, release_id)
    if not conversation:
        st.markdown(t("**¿Por dónde empezar?**"))
        questions = starter_questions(catalog)
        if not questions:
            st.caption(t("Escribí una pregunta sobre el negocio. Ejemplo: ¿Qué es un cliente activo?"))
        for row_start in range(0, len(questions), 3):
            columns = st.columns(3)
            for column, (index, question) in zip(columns, enumerate(questions[row_start:row_start + 3], start=row_start)):
                if column.button(question, key=f"argos-starter-{project_id}-{index}", width="stretch"):
                    _ask(service, project_id, release_id, question)
    else:
        if st.button(t("Limpiar conversación"), type="tertiary", icon=":material/delete_sweep:", key=f"argos-clear-{project_id}"):
            conversation.clear()
            st.rerun()
        for position, exchange in enumerate(conversation):
            with st.chat_message("user"):
                st.markdown(_plain(exchange["question"]))
            with st.chat_message("assistant"):
                _render_answer(service, project_id, release_id, exchange["result"], catalog, position)

    question = st.chat_input(t("Preguntá sobre el negocio"), key=f"argos-chat-input-{project_id}")
    if question and question.strip():
        _ask(service, project_id, release_id, question)


def _render_answer(service, project_id: str, release_id: str, result: dict[str, object], catalog, position: int) -> None:
    status = str(dict(result.get("manifest", {})).get("status", ""))
    answer = _plain(result.get("answer", ""))
    if status == "abstained":
        st.warning(answer, icon=":material/block:")
    else:
        st.markdown(answer)
    if result.get("interpretation"):
        st.caption(_plain(result["interpretation"]))
    live_query = result.get("live_query")
    if isinstance(live_query, dict):
        rows = [row for row in live_query.get("rows", []) if isinstance(row, dict)]
        _render_rows(rows, catalog.get(str(live_query.get("query_name", "")), {}))
    follow_ups = list(result.get("suggested_questions", []) or [])
    if follow_ups:
        columns = st.columns(min(3, len(follow_ups)))
        for index, follow_up in enumerate(follow_ups[:3]):
            if columns[index].button(follow_up, key=f"argos-follow-up-{project_id}-{position}-{index}", width="stretch"):
                _ask(service, project_id, release_id, follow_up)
    with st.expander(t("Evidencia y trazabilidad")):
        _render_traceability(result)


def _render_rows(rows: list[dict[str, object]], specification: dict[str, object]) -> None:
    if not rows:
        return
    visualization = infer_visualization(rows, specification)
    if visualization and visualization["type"] == "metrics":
        fields = list(visualization["fields"])
        columns = st.columns(len(fields))
        for column, field in zip(columns, fields):
            column.metric(field.replace("_", " ").capitalize(), str(rows[0].get(field, "Sin dato")))
    elif visualization and visualization["type"] == "bar":
        st.bar_chart(
            {str(row.get(visualization["x"], "")): float(row.get(visualization["y"]) or 0) for row in rows},
            height=240,
        )
    if len(rows) > 1 or not visualization:
        with st.expander(t('Datos ({v0} fila(s))', v0=len(rows)), expanded=not visualization):
            st.dataframe(rows, width="stretch", hide_index=True)


def _render_traceability(result: dict[str, object]) -> None:
    manifest = dict(result.get("manifest", {}))
    status = str(manifest.get("status", ""))
    st.caption(t('Estado: {v0} · Registro: {v1}', v0=STATUS_LABELS.get(status, status or 'desconocido'), v1=result.get('package_path', 'sin ruta')))
    advisory = result.get("reasoning_advisory")
    if isinstance(advisory, dict):
        st.caption(str(advisory.get("message", "")))
        if advisory.get("model_used"):
            st.caption(t('Motor: {v0}', v0=advisory['model_used']))
    live_query = result.get("live_query")
    if isinstance(live_query, dict):
        st.caption(
            t('Consulta: {v0} · {v1} · {v2} fila(s)', v0=live_query.get('query_name', 'consulta'), v1=live_query.get('operation', 'SELECT'), v2=len(live_query.get('rows', [])))
        )
    retrieval = result.get("retrieval", [])
    if retrieval:
        st.dataframe(retrieval, width="stretch", hide_index=True)


def _plain(value: object) -> str:
    """Keep currency values from being parsed as Streamlit math."""
    return str(value).replace("$", "\\$")


# ---------------------------------------------------------------- Analistas

def _render_analyst_workspace(service: WorkbenchService, project_id: str, release_id: str, catalog) -> None:
    st.markdown(t("**Consultas autorizadas en esta release**"))
    if catalog:
        st.dataframe(
            localize_rows([
                {
                    "Consulta": name,
                    "Descripción": spec.get("description", ""),
                    "Origen": spec.get("adapter", ""),
                    "Parámetros": ", ".join(spec.get("allowed_parameters", [])),
                    "Máx. filas": spec.get("max_rows", ""),
                    "Pregunta de ejemplo": spec.get("example_question", ""),
                }
                for name, spec in catalog.items()
            ]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption(t("La release no tiene consultas de datos; Argos responde solo con el conocimiento aprobado."))

    st.markdown(t("**Batería de evaluación**"))
    st.caption(
        t("Define qué debe responder Argos y de qué debe abstenerse. Cada ejecución valida el estado esperado "
        "y, si corresponde, la evidencia recuperada.")
    )
    cases_key = f"argos-evaluation-cases-{project_id}"
    if st.button(t("Preparar batería base"), key=f"argos-evaluation-suggest-{project_id}"):
        try:
            suggested = service.suggest_argos_evaluation_cases(project_id, release_id)
        except FileNotFoundError as exc:
            st.error(str(exc))
        else:
            st.session_state[cases_key] = "\n".join(
                t('{v0} | {v1} | {v2}', v0=case['question'], v1=case['expected_status'], v2=case['expected_item_name']) for case in suggested
            )
            st.rerun()
    cases_text = st.text_area(
        t("Un caso por línea: pregunta | answered o abstained | evidencia esperada (opcional)"),
        key=cases_key,
        placeholder=t("¿Qué es Cliente Activo? | answered | Cliente Activo\n¿Qué planeta es más grande? | abstained |"),
        height=160,
    )
    if st.button(t("Ejecutar batería"), type="primary", key=f"argos-evaluation-run-{project_id}"):
        cases, invalid = parse_evaluation_cases(cases_text)
        if invalid:
            st.error(t("Formato inválido en líneas: ") + ", ".join(invalid))
        elif not cases:
            st.error(t("Cargá al menos un caso."))
        else:
            try:
                with st.spinner(t("Ejecutando batería…")):
                    st.session_state[f"argos-evaluation-result-{project_id}"] = service.evaluate_argos_release(
                        project_id, release_id, cases
                    )
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
    evaluation = st.session_state.get(f"argos-evaluation-result-{project_id}")
    if not evaluation:
        return
    summary = dict(evaluation["summary"])
    metrics = st.columns(3)
    metrics[0].metric(t("Casos"), summary["total"])
    metrics[1].metric(t("Correctos"), summary["passed"])
    metrics[2].metric(t("Fallidos"), summary["failed"])
    st.dataframe(
        localize_rows([
            {
                "Correcto": case["passed"],
                "Pregunta": case["question"],
                "Esperado": STATUS_LABELS.get(case["expected_status"], case["expected_status"]),
                "Obtenido": STATUS_LABELS.get(case["actual_status"], case["actual_status"]),
                "Evidencia": ", ".join(case["retrieved_item_names"]),
                "Motivo": case["failure_reason"],
            }
            for case in evaluation["cases"]
        ]),
        width="stretch",
        hide_index=True,
        column_config={t("Correcto"): st.column_config.CheckboxColumn()},
    )
    st.caption(t('Paquete de evaluación: {v0}', v0=evaluation['package_path']))
    questions = {index: case["question"] for index, case in enumerate(evaluation["cases"])}
    selected = st.selectbox(
        t("Ver respuesta de un caso"), list(questions), format_func=option_labels(list(questions), questions.get), key=f"argos-evaluation-detail-{project_id}"
    )
    investigation = dict(evaluation["cases"][selected].get("investigation", {}))
    st.write(_plain(investigation.get("answer", "Sin respuesta")))
    live_query = investigation.get("live_query")
    if isinstance(live_query, dict) and live_query.get("rows"):
        st.dataframe(live_query["rows"], width="stretch", hide_index=True)
