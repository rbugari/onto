"""Atlas screen: scope, systems, business context and diagnosis in four guided steps."""
from __future__ import annotations

from collections import Counter

import streamlit as st

from ontology_workbench.atlas import PLATFORM_LABELS
from ontology_workbench.context_scanner import (
    SUPPORTED_DOCUMENT_TYPES,
    SUPPORTED_FILE_EXTENSIONS,
    load_llm_settings,
)
from ontology_workbench.service import USE_CASE_PRIORITIES, WorkbenchService
from onto_ui.common import reviewer
from onto_ui.labels import (
    ACCESS_MODE_LABELS,
    ATLAS_REVIEW_LABELS,
    DIMENSION_LABELS,
    DOCUMENT_TYPE_LABELS,
    GAP_CATEGORY_LABELS,
    INTERPRETATION_LABELS,
    METADATA_FILE_TYPES,
    METADATA_FORMAT_HINTS,
    PRIORITY_LABELS,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    SOURCE_STATUS_LABELS,
    short_timestamp,
)

STEP_TITLES = ["1. Alcance", "2. Fuentes", "3. Contexto de negocio", "4. Diagnóstico"]


def render_atlas(service: WorkbenchService, project_id: str) -> None:
    project = service.get_project(project_id)
    documents = service.list_context_documents(project.id)
    inventory = service.get_business_context_inventory(project.id)
    assessments = service.list_atlas_assessments(project.id)

    st.title("Atlas · Diagnóstico de preparación")
    st.caption(
        "Reúne la metadata de todos los sistemas del dominio y la documentación de negocio para saber "
        "qué está listo, qué falta, cómo se conectan los sistemas y qué podrá implementar la plataforma destino."
    )
    _render_progress(project, documents, inventory, assessments)

    scope_tab, sources_tab, context_tab, diagnosis_tab = st.tabs(STEP_TITLES)
    with scope_tab:
        _render_scope(service, project)
    with sources_tab:
        _render_sources(service, project)
    with context_tab:
        _render_context(service, project.id, documents, inventory)
    with diagnosis_tab:
        _render_diagnosis(service, project, assessments)


def _render_progress(project, documents, inventory, assessments) -> None:
    has_scope = all(project.metadata.get(key) for key in ("client_id", "domain_id", "data_product_id"))
    inventoried = [source for source in project.sources if source.status == "inventoried"]
    pending_sources = [source for source in project.sources if source.status != "inventoried"]
    context_ready = bool(inventory) and inventory.get("status") != "invalidated"
    latest = assessments[0] if assessments else None
    is_stale = bool(latest) and str(latest.get("created_at", "")) < project.updated_at
    review_status = str(dict((latest or {}).get("assessment_review", {})).get("status", "pending_review"))

    steps = [
        ("Alcance", has_scope and bool(project.use_cases),
         f"{len(project.use_cases)} caso(s) de uso" if project.use_cases else "Sin casos de uso"),
        ("Fuentes", bool(inventoried) and not pending_sources,
         f"{len(inventoried)}/{len(project.sources)} sistemas inventariados" if project.sources else "Sin sistemas"),
        ("Contexto", context_ready,
         f"{len(documents)} documento(s) analizados" if context_ready else f"{len(documents)} documento(s), sin analizar"),
        ("Diagnóstico", bool(latest) and not is_stale,
         "Desactualizado" if is_stale else ("Generado" if latest else "Pendiente")),
        ("Revisión", review_status == "reviewed", ATLAS_REVIEW_LABELS.get(review_status, review_status)),
    ]
    columns = st.columns(len(steps))
    for column, (label, done, detail) in zip(columns, steps):
        with column:
            icon = ":material/check_circle:" if done else ":material/radio_button_unchecked:"
            st.markdown(f"{icon} **{label}**")
            st.caption(detail)

    next_step = next((label for label, done, _ in steps if not done), None)
    messages = {
        "Alcance": "Definí cliente, dominio y al menos un caso de uso en la pestaña **Alcance**.",
        "Fuentes": "Registrá todos los sistemas del dominio y cargá su metadata en **Fuentes**.",
        "Contexto": "Subí glosarios, KPIs o procesos y analizalos en **Contexto de negocio**.",
        "Diagnóstico": "Generá el diagnóstico en la pestaña **Diagnóstico**.",
        "Revisión": "Revisá brechas y registrá la decisión en **Diagnóstico**.",
    }
    if next_step:
        st.info(f"Siguiente paso: {messages[next_step]}", icon=":material/arrow_forward:")
    else:
        st.success("Diagnóstico revisado. Podés continuar en Nexo para validar el conocimiento y prepararlo para la plataforma.")


# ---------------------------------------------------------------- Alcance

def _render_scope(service: WorkbenchService, project) -> None:
    st.subheader("Qué se evalúa")
    with st.form(f"atlas-scope-{project.id}"):
        columns = st.columns(4)
        client_id = columns[0].text_input("Cliente", value=project.metadata.get("client_id", project.id))
        domain_id = columns[1].text_input("Dominio", value=project.metadata.get("domain_id", ""))
        data_product_id = columns[2].text_input(
            "Producto de datos", value=project.metadata.get("data_product_id", project.id)
        )
        owner = columns[3].text_input("Responsable del dominio", value=project.metadata.get("owner", ""))
        if st.form_submit_button("Guardar alcance"):
            try:
                service.update_assessment_scope(project.id, client_id, domain_id, data_product_id, owner)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.rerun()

    st.subheader("Casos de uso")
    st.caption(
        "Cada caso de uso indica qué pregunta de negocio se quiere responder y qué sistemas necesita. "
        "Atlas los usa para priorizar las brechas."
    )
    source_names = {source.source_id: source.name for source in project.sources}
    if project.use_cases:
        st.dataframe(
            [
                {
                    "Caso de uso": use_case.name,
                    "Pregunta de negocio": use_case.business_question,
                    "Responsable": use_case.owner,
                    "Prioridad": PRIORITY_LABELS.get(use_case.priority, use_case.priority),
                    "Sistemas": ", ".join(source_names.get(item, item) for item in use_case.source_ids),
                }
                for use_case in project.use_cases
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Todavía no hay casos de uso.")

    add_column, delete_column = st.columns((3, 1))
    with add_column, st.expander("Agregar caso de uso", expanded=not project.use_cases):
        if not project.sources:
            st.caption("Tip: registrá primero los sistemas en **Fuentes** para poder vincularlos.")
        with st.form(f"atlas-use-case-{project.id}", clear_on_submit=True):
            name = st.text_input("Nombre", placeholder="Ejemplo: Rentabilidad por cliente", key=f"atlas-use-case-name-{project.id}")
            question = st.text_area("Pregunta de negocio", placeholder="¿Qué clientes generan más margen?", height=70)
            columns = st.columns(2)
            use_case_owner = columns[0].text_input("Responsable")
            priority = columns[1].selectbox(
                "Prioridad", USE_CASE_PRIORITIES, index=1, format_func=PRIORITY_LABELS.get
            )
            linked_sources = st.multiselect(
                "Sistemas que necesita", list(source_names), format_func=source_names.get,
                key=f"atlas-use-case-sources-{project.id}",
            )
            if st.form_submit_button("Agregar caso de uso", type="primary", key=f"atlas-use-case-submit-{project.id}"):
                try:
                    service.add_use_case(project.id, name, question, use_case_owner, priority, linked_sources)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    if project.use_cases:
        with delete_column, st.expander("Quitar"):
            use_case_names = {item.use_case_id: item.name for item in project.use_cases}
            selected = st.selectbox(
                "Caso de uso", list(use_case_names), format_func=use_case_names.get,
                key=f"atlas-use-case-delete-{project.id}",
            )
            if st.button("Quitar caso de uso", key=f"atlas-use-case-delete-button-{project.id}"):
                service.delete_use_case(project.id, selected)
                st.rerun()


# ---------------------------------------------------------------- Fuentes

def _render_sources(service: WorkbenchService, project) -> None:
    sources = project.sources
    inventoried = [source for source in sources if source.status == "inventoried"]
    metrics = st.columns(4)
    metrics[0].metric("Sistemas en alcance", len(sources))
    metrics[1].metric("Inventariados", len(inventoried))
    metrics[2].metric("Tablas", sum(source.object_counts.get("tables", 0) for source in sources))
    metrics[3].metric("Columnas", sum(source.object_counts.get("columns", 0) for source in sources))

    if sources:
        st.dataframe(
            [
                {
                    "Sistema": source.name,
                    "Plataforma": PLATFORM_LABELS.get(source.platform, source.platform),
                    "Estado": SOURCE_STATUS_LABELS.get(source.status, source.status),
                    "Responsable": source.owner or "Sin asignar",
                    "Acceso": ACCESS_MODE_LABELS.get(source.access_mode, source.access_mode),
                    "Tablas": source.object_counts.get("tables", 0),
                    "Columnas": source.object_counts.get("columns", 0),
                    "Archivo": source.filename,
                    "Inventariado": short_timestamp(source.inventoried_at),
                }
                for source in sources
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(
            "Registrá cada sistema que participa del dominio (ERP, lakehouse, CRM, modelos de BI, planillas). "
            "No hace falta que estén en la misma plataforma."
        )

    register_column, load_column = st.columns(2)
    with register_column, st.container(border=True):
        st.markdown("**Agregar sistema**")
        with st.form(f"atlas-source-add-{project.id}", clear_on_submit=True):
            name = st.text_input("Nombre", placeholder="Ejemplo: ERP operativo", key=f"atlas-source-name-{project.id}")
            platform = st.selectbox(
                "Plataforma", list(PLATFORM_LABELS), format_func=PLATFORM_LABELS.get,
                key=f"atlas-source-platform-{project.id}",
            )
            owner = st.text_input("Responsable", key=f"atlas-source-owner-{project.id}")
            description = st.text_input("Descripción (opcional)")
            if st.form_submit_button("Agregar sistema", type="primary", key=f"atlas-source-submit-{project.id}"):
                try:
                    service.register_data_source(project.id, name, platform, owner, description)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()

    with load_column, st.container(border=True):
        st.markdown("**Cargar metadata de un sistema**")
        if not sources:
            st.caption("Primero agregá un sistema.")
        else:
            source_by_id = {source.source_id: source for source in sources}
            selected_id = st.selectbox(
                "Sistema",
                list(source_by_id),
                format_func=lambda item: f"{source_by_id[item].name} · {SOURCE_STATUS_LABELS[source_by_id[item].status]}",
                key=f"atlas-source-load-{project.id}",
            )
            selected = source_by_id[selected_id]
            st.caption(METADATA_FORMAT_HINTS.get(selected.platform, METADATA_FORMAT_HINTS["other"]))
            uploaded = st.file_uploader(
                "Archivo de metadata", type=METADATA_FILE_TYPES, key=f"atlas-source-file-{project.id}-{selected_id}"
            )
            if selected.status == "inventoried":
                st.caption("Volver a cargar reemplaza los objetos de este sistema; los demás no cambian.")
            if uploaded is not None and st.button(
                "Inventariar sistema", type="primary", key=f"atlas-source-import-{project.id}"
            ):
                try:
                    _, summary = service.import_source_metadata_file(
                        project.id, selected_id, uploaded.name, uploaded.getvalue()
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.toast(f"{selected.name}: {summary['tables']} tablas y {summary['columns']} columnas.")
                    st.rerun()

    _render_fabric_connector(service, project.id)
    if sources:
        _render_source_editor(service, project)
        _render_source_objects(project)


def _render_fabric_connector(service: WorkbenchService, project_id: str) -> None:
    with st.expander("Conexión directa a Microsoft Fabric (solo lectura)"):
        st.caption(
            "Usa la identidad Entra configurada en el entorno. Lee solo metadata (INFORMATION_SCHEMA); "
            "no lee filas ni publica cambios."
        )
        filter_columns = st.columns(2)
        schema_name = filter_columns[0].text_input(
            "Schema exacto (opcional)", placeholder="gold_sic", key=f"fabric-schema-{project_id}"
        )
        table_pattern = filter_columns[1].text_input(
            "Filtrar tablas por nombre (opcional)", placeholder="fact_", key=f"fabric-table-pattern-{project_id}"
        )
        action_columns = st.columns(2)
        if action_columns[0].button("Comprobar conexión", key=f"fabric-check-{project_id}"):
            try:
                connection = service.check_fabric_connection()
            except Exception as exc:
                st.error(str(exc))
            else:
                st.success(f"Conexión confirmada: {connection['identity']} · {connection['database']}")
        if action_columns[1].button("Leer metadata", key=f"fabric-discover-{project_id}"):
            try:
                st.session_state[f"fabric-discovery-{project_id}"] = service.discover_fabric_metadata(
                    project_id, table_pattern, schema_name
                )
            except Exception as exc:
                st.error(str(exc))
        discovery = st.session_state.get(f"fabric-discovery-{project_id}")
        if discovery:
            st.success(f"{len(discovery['tables'])} tablas/vistas y {len(discovery['columns'])} columnas leídas.")
            st.dataframe(discovery["tables"], width="stretch", hide_index=True, height=200)
            if st.button("Incorporar como sistema Fabric", type="primary", key=f"fabric-import-{project_id}"):
                try:
                    imported = service.import_fabric_metadata(project_id, discovery)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.pop(f"fabric-discovery-{project_id}", None)
                    st.toast(f"Fabric: {imported['added']} objetos nuevos incorporados.")
                    st.rerun()


def _render_source_editor(service: WorkbenchService, project) -> None:
    with st.expander("Editar o quitar un sistema"):
        source_by_id = {source.source_id: source for source in project.sources}
        selected_id = st.selectbox(
            "Sistema", list(source_by_id), format_func=lambda item: source_by_id[item].name,
            key=f"atlas-source-edit-select-{project.id}",
        )
        selected = source_by_id[selected_id]
        platforms = list(PLATFORM_LABELS)
        with st.form(f"atlas-source-edit-{project.id}-{selected_id}"):
            columns = st.columns(3)
            name = columns[0].text_input("Nombre", value=selected.name)
            platform = columns[1].selectbox(
                "Plataforma", platforms, index=platforms.index(selected.platform) if selected.platform in platforms else len(platforms) - 1,
                format_func=PLATFORM_LABELS.get,
            )
            owner = columns[2].text_input("Responsable", value=selected.owner)
            description = st.text_input("Descripción", value=selected.description)
            if st.form_submit_button("Guardar cambios"):
                try:
                    service.update_data_source(project.id, selected_id, name, platform, owner, description)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
        confirm = st.checkbox(
            f"Quitar '{selected.name}' y sus objetos inventariados (se guarda un snapshot antes)",
            key=f"atlas-source-delete-confirm-{project.id}-{selected_id}",
        )
        if st.button("Quitar sistema", disabled=not confirm, key=f"atlas-source-delete-{project.id}"):
            service.delete_data_source(project.id, selected_id)
            st.rerun()


def _render_source_objects(project) -> None:
    with st.expander("Ver objetos inventariados"):
        source_names = {source.source_id: source.name for source in project.sources}
        options = ["all", *source_names]
        selected = st.selectbox(
            "Sistema", options,
            format_func=lambda item: "Todos" if item == "all" else source_names.get(item, item),
            key=f"atlas-objects-filter-{project.id}",
        )
        columns_by_table = Counter(
            (concept.metadata.get("source.id", ""), concept.metadata.get("bim.table") or
             f"{concept.metadata.get('fabric.schema', '')}.{concept.metadata.get('fabric.table', '')}")
            for concept in project.concepts
            if "column" in concept.tags
        )
        rows = [
            {
                "Sistema": source_names.get(concept.metadata.get("source.id", ""), "Sin sistema"),
                "Tabla": concept.name,
                "Columnas": columns_by_table.get((concept.metadata.get("source.id", ""), concept.name), 0),
            }
            for concept in project.concepts
            if "table" in concept.tags and (selected == "all" or concept.metadata.get("source.id") == selected)
        ]
        st.dataframe(rows, width="stretch", hide_index=True, height=min(400, 38 + 35 * max(len(rows), 1)))


# ---------------------------------------------------------------- Contexto

def _render_context(service: WorkbenchService, project_id: str, documents, inventory) -> None:
    settings = load_llm_settings()
    st.caption(
        f"Motor de extracción: {settings.provider} · {settings.model}"
        if settings.enabled
        else "Motor de extracción: reglas locales (sin LLM, sin costo)."
    )
    upload_column, list_column = st.columns((2, 3))
    with upload_column, st.container(border=True):
        st.markdown("**Subir documentos**")
        doc_type = st.selectbox(
            "Tipo", SUPPORTED_DOCUMENT_TYPES, format_func=lambda item: DOCUMENT_TYPE_LABELS.get(item, item),
            key=f"atlas-doc-type-{project_id}",
        )
        uploaded_files = st.file_uploader(
            "Glosarios, KPIs, procesos, diccionarios…",
            type=SUPPORTED_FILE_EXTENSIONS,
            accept_multiple_files=True,
            key=f"context-files-{project_id}",
        )
        if uploaded_files and st.button("Subir", type="primary", key=f"upload-docs-{project_id}"):
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
                st.rerun()

    with list_column:
        if not documents:
            st.info("Todavía no hay documentos cargados.")
        else:
            st.dataframe(
                [
                    {
                        "Archivo": document.filename,
                        "Tipo": DOCUMENT_TYPE_LABELS.get(document.doc_type, document.doc_type),
                        "Estado": document.extraction_status,
                        "Caracteres": document.extracted_chars,
                        "Subido": short_timestamp(document.uploaded_at),
                    }
                    for document in documents
                ],
                width="stretch",
                hide_index=True,
            )
            integrity = service.get_context_document_integrity(project_id)
            if integrity["duplicate_document_ids"]:
                st.warning("Hay documentos heredados con IDs duplicados; la evidencia puede no ser trazable.")
                if st.button("Reparar IDs y volver a extraer", key=f"repair-doc-ids-{project_id}"):
                    service.repair_context_document_ids(project_id)
                    st.rerun()
            if st.button("Analizar contexto de negocio", type="primary", key=f"scan-context-{project_id}"):
                try:
                    with st.spinner("Analizando documentos…"):
                        service.scan_business_context(project_id)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()

    if inventory and inventory.get("status") == "invalidated":
        st.warning("El análisis anterior quedó invalidado. Volvé a analizar los documentos.")
    elif inventory:
        _render_context_inventory(project_id, inventory)

    with st.expander("Configuración del motor LLM (técnico)"):
        st.code(
            "\n".join(
                [
                    "ONTO_LLM_PROVIDER=disabled | openai | azure_openai | ollama",
                    "ONTO_LLM_MODEL=gpt-4.1-mini | deployment-name | llama3.1:8b",
                    "ONTO_LLM_API_KEY=...",
                    "ONTO_LLM_BASE_URL=https://api.openai.com/v1",
                    "ONTO_AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com",
                    "ONTO_AZURE_OPENAI_DEPLOYMENT=<deployment>",
                    "ONTO_LLM_CONFIG_PATH=<ruta a configuración compartida>",
                ]
            ),
            language="bash",
        )
        st.caption("Sin proveedor configurado se usan reglas locales. Solo se envía contenido autorizado.")


def _render_context_inventory(project_id: str, inventory: dict[str, object]) -> None:
    st.subheader("Resultado del análisis")
    views = {
        "definitions": ("Definiciones", lambda item: {"Término": item.get("term"), "Definición": item.get("definition")}),
        "kpis": ("KPIs", lambda item: {"KPI": item.get("name") or item.get("text")}),
        "business_rules": ("Reglas", lambda item: {"Regla": item.get("text") or item.get("rule")}),
        "candidate_entities": ("Entidades vinculadas", lambda item: {"Término": item.get("term"), "Objeto técnico": item.get("matched_semantic_object")}),
        "questions_for_workshop": ("Preguntas para taller", lambda item: {"Pregunta": item.get("question")}),
    }
    counts = {key: len(inventory.get(key, []) or []) for key in views}
    selected = st.segmented_control(
        "Ver",
        list(views),
        format_func=lambda key: f"{views[key][0]} ({counts[key]})",
        default="definitions",
        key=f"atlas-context-view-{project_id}",
        label_visibility="collapsed",
    ) or "definitions"
    if inventory.get("scanner_warning"):
        st.warning(str(inventory["scanner_warning"]))
    label, to_row = views[selected]
    items = [item for item in inventory.get(selected, []) or [] if isinstance(item, dict)]
    if not items:
        st.caption(f"No se detectaron {label.lower()}.")
        return
    rows = []
    for item in items:
        row = to_row(item)
        row["Documento"] = item.get("source_filename") or item.get("source_document_id", "")
        row["Estado"] = item.get("status", "")
        rows.append(row)
    st.dataframe(rows, width="stretch", hide_index=True)


# ---------------------------------------------------------------- Diagnóstico

def _render_diagnosis(service: WorkbenchService, project, assessments: list[dict[str, object]]) -> None:
    client_id = project.metadata.get("client_id", project.id)
    domain_id = project.metadata.get("domain_id", "default")
    data_product_id = project.metadata.get("data_product_id", project.id)
    action_column, info_column = st.columns((1, 3))
    if action_column.button("Generar diagnóstico", type="primary", key=f"atlas-generate-{project.id}"):
        try:
            with st.spinner("Generando diagnóstico…"):
                service.create_atlas_assessment(project.id, client_id, domain_id, data_product_id)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.rerun()
    info_column.caption(
        f"Cliente **{client_id}** · Dominio **{domain_id}** · Producto de datos **{data_product_id}**. "
        "El diagnóstico es determinista (sin LLM) y no aprueba una ontología ni publica en sistemas externos."
    )
    if not assessments:
        st.info("Todavía no hay diagnósticos para este proyecto.")
        return
    if str(assessments[0].get("created_at", "")) < project.updated_at:
        st.warning("Hubo cambios en el proyecto después del último diagnóstico. Conviene generarlo de nuevo.")

    runs = {str(item["run_id"]): item for item in assessments}
    run_id = st.selectbox(
        "Diagnóstico",
        list(runs),
        format_func=lambda item: _run_label(runs[item]),
        key=f"atlas-run-{project.id}",
    )
    details = service.get_atlas_assessment(project.id, run_id)
    score = dict(details["readiness_score"])
    gaps = list(details["gap_backlog"])
    source_inventory = dict(details["source_inventory"])

    headline = st.columns(4)
    headline[0].metric("Puntaje basal", f"{score.get('overall_score', 0)} / 5")
    headline[1].metric("Lectura", INTERPRETATION_LABELS.get(str(score.get("interpretation")), "-"))
    headline[2].metric("Brechas", len(gaps), f"{sum(gap['severity'] == 'high' for gap in gaps)} altas", delta_color="off")
    headline[3].metric("Sistemas inventariados", dict(source_inventory.get("summary", {})).get("technical_sources", 0))

    dimension_columns = st.columns(len(score.get("dimensions", [])) or 1)
    for column, dimension in zip(dimension_columns, score.get("dimensions", [])):
        with column:
            label = DIMENSION_LABELS.get(dimension["dimension"], dimension["dimension"])
            st.progress(dimension["score"] / dimension["max_score"], text=f"{label}: {dimension['score']}/5")
            st.caption(dimension["evidence"])

    views = ["Brechas", "Mapa entre sistemas", "Sistemas", "Informe"]
    view = st.segmented_control(
        "Vista", views, default="Brechas", key=f"atlas-diagnosis-view-{project.id}", label_visibility="collapsed"
    ) or "Brechas"
    if view == "Brechas":
        _render_gaps(project, gaps)
    elif view == "Mapa entre sistemas":
        _render_cross_source_map(dict(details.get("cross_source_map", {})))
    elif view == "Sistemas":
        _render_assessed_sources(source_inventory)
    else:
        st.download_button(
            "Descargar informe (Markdown)",
            data=str(details["execution_summary"]),
            file_name=f"atlas-{run_id}.md",
            mime="text/markdown",
            key=f"atlas-report-{run_id}",
        )
        with st.container(height=500, border=True):
            st.markdown(str(details["execution_summary"]))
        st.caption(f"Paquete local: {details['package_path']}")

    _render_review(service, project.id, run_id, dict(details.get("assessment_review", {})))


def _run_label(assessment: dict[str, object]) -> str:
    summary = dict(assessment.get("summary", {}))
    review = dict(assessment.get("assessment_review", {}))
    parts = [short_timestamp(assessment.get("created_at"))]
    if summary:
        parts.append(f"{summary.get('overall_score')}/5 · {summary.get('gaps')} brechas")
    parts.append(ATLAS_REVIEW_LABELS.get(str(review.get("status", "pending_review")), "-"))
    return " · ".join(parts)


def _render_gaps(project, gaps: list[dict[str, object]]) -> None:
    if not gaps:
        st.success("No se detectaron brechas con las reglas basales. Igual hace falta revisión funcional.")
        return
    source_names = {source.source_id: source.name for source in project.sources}
    use_case_names = {use_case.use_case_id: use_case.name for use_case in project.use_cases}
    filter_columns = st.columns(2)
    severities = filter_columns[0].multiselect(
        "Severidad", list(SEVERITY_LABELS), default=list(SEVERITY_LABELS),
        format_func=SEVERITY_LABELS.get, key=f"atlas-gap-severity-{project.id}",
    )
    categories = sorted({str(gap.get("category", "gobierno")) for gap in gaps})
    selected_categories = filter_columns[1].multiselect(
        "Categoría", categories, default=categories,
        format_func=lambda item: GAP_CATEGORY_LABELS.get(item, item), key=f"atlas-gap-category-{project.id}",
    )
    visible = sorted(
        (
            gap for gap in gaps
            if gap["severity"] in severities and str(gap.get("category", "gobierno")) in selected_categories
        ),
        key=lambda gap: SEVERITY_ORDER.get(str(gap["severity"]), 9),
    )
    st.dataframe(
        [
            {
                "Severidad": SEVERITY_LABELS.get(str(gap["severity"]), gap["severity"]),
                "Categoría": GAP_CATEGORY_LABELS.get(str(gap.get("category")), gap.get("category", "")),
                "Sistema": source_names.get(str(gap.get("source_id", "")), gap.get("source_id", "")),
                "Casos de uso": ", ".join(use_case_names.get(item, item) for item in gap.get("use_case_ids", [])),
                "Hallazgo": gap["message"],
                "Acción sugerida": gap["recommendation"],
            }
            for gap in visible
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Hallazgo": st.column_config.TextColumn(width="large"),
            "Acción sugerida": st.column_config.TextColumn(width="large"),
        },
    )


def _render_cross_source_map(cross_source_map: dict[str, object]) -> None:
    if not cross_source_map:
        st.info("Este diagnóstico se generó antes del mapa entre sistemas. Generá uno nuevo.")
        return
    summary = dict(cross_source_map.get("summary", {}))
    if summary.get("sources", 0) < 2:
        st.info("Se necesitan al menos dos sistemas inventariados para comparar entidades entre ellos.")
        return
    metrics = st.columns(3)
    metrics[0].metric("Entidades detectadas", summary.get("entities", 0))
    metrics[1].metric("En más de un sistema", summary.get("shared_entities", 0))
    metrics[2].metric("Con clave común", summary.get("shared_with_common_key", 0))
    st.caption(str(cross_source_map.get("warning", "")))
    shared = list(cross_source_map.get("shared_entities", []))
    if shared:
        st.dataframe(
            [
                {
                    "Entidad": row["entity"],
                    "Sistemas": ", ".join(row["sources"]),
                    "Tablas": " | ".join(", ".join(tables) for tables in dict(row["tables"]).values()),
                    "Clave común": row.get("common_key") or "No identificada",
                    "Columnas clave": " | ".join(", ".join(cols) for cols in dict(row.get("key_columns", {})).values()),
                    "Otras claves compartidas": ", ".join(row.get("shared_reference_keys", [])),
                }
                for row in shared
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.warning("Ninguna entidad aparece en más de un sistema con un nombre reconocible.")
    single = list(cross_source_map.get("single_source_entities", []))
    if single:
        with st.expander(f"Entidades presentes en un solo sistema ({len(single)})"):
            st.dataframe(
                [
                    {"Entidad": row["entity"], "Sistema": ", ".join(row["sources"]),
                     "Tablas": ", ".join(t for tables in dict(row["tables"]).values() for t in tables)}
                    for row in single
                ],
                width="stretch",
                hide_index=True,
            )


def _render_assessed_sources(source_inventory: dict[str, object]) -> None:
    rows = [
        {
            "Sistema": source.get("name", source.get("source_id")),
            "Plataforma": source.get("platform_label", source.get("platform", "")),
            "Estado": SOURCE_STATUS_LABELS.get(str(source.get("status")), source.get("status", "")),
            "Responsable": source.get("owner") or "Sin asignar",
            "Tablas": dict(source.get("object_counts", {})).get("tables", 0),
            "Columnas": dict(source.get("object_counts", {})).get("columns", 0),
            "Formato": source.get("source_format", ""),
            "Integridad": source.get("integrity_status", ""),
            "SHA-256": str(source.get("content_sha256", ""))[:12],
        }
        for source in [
            *source_inventory.get("technical_sources", []),
            *source_inventory.get("declared_sources", []),
        ]
    ]
    st.markdown("**Sistemas técnicos**")
    st.dataframe(rows, width="stretch", hide_index=True)
    documents = list(source_inventory.get("sources", []))
    if documents:
        st.markdown("**Documentos**")
        st.dataframe(
            [
                {
                    "Archivo": item["filename"],
                    "Tipo": DOCUMENT_TYPE_LABELS.get(item["document_type"], item["document_type"]),
                    "Estado": item["extraction_status"],
                    "SHA-256": str(item["content_sha256"])[:12],
                }
                for item in documents
            ],
            width="stretch",
            hide_index=True,
        )


def _render_review(service: WorkbenchService, project_id: str, run_id: str, review: dict[str, object]) -> None:
    if not review:
        return
    with st.container(border=True):
        st.markdown("**Revisión del diagnóstico**")
        st.caption("Registra la decisión humana sobre este diagnóstico. No aprueba una ontología.")
        with st.form(f"atlas-review-{run_id}"):
            columns = st.columns(3)
            options = list(ATLAS_REVIEW_LABELS)
            current = str(review.get("status", "pending_review"))
            status = columns[0].selectbox(
                "Decisión", options, index=options.index(current) if current in options else 0,
                format_func=ATLAS_REVIEW_LABELS.get,
            )
            reviewer_name = columns[1].text_input("Revisor/a", value=str(review.get("reviewer") or reviewer()[0]))
            reviewer_role = columns[2].text_input("Rol", value=str(review.get("reviewer_role") or reviewer()[1]))
            note = st.text_area("Nota", value=str(review.get("note", "")), height=80)
            if st.form_submit_button("Guardar revisión"):
                try:
                    service.update_atlas_review(project_id, run_id, status, reviewer_name, reviewer_role, note)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
