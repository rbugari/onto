"""Atlas screen: scope, systems, business context and diagnosis in four guided steps."""
from __future__ import annotations

from collections import Counter

import streamlit as st

from onto_ui.i18n import localize_rows, localized_tabs, option_labels, t
from onto_ui.i18n import reason_text, request_text

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

    st.title(t("Atlas · Diagnóstico de preparación"))
    st.caption(
        t("Reúne la metadata de todos los sistemas del dominio y la documentación de negocio para saber "
        "qué está listo, qué falta, cómo se conectan los sistemas y qué podrá implementar la plataforma destino.")
    )
    _render_progress(project, documents, inventory, assessments)

    scope_tab, sources_tab, context_tab, diagnosis_tab = localized_tabs(STEP_TITLES, key=f"atlas-tabs-{project_id}")
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
         t('{v0} caso(s) de uso', v0=len(project.use_cases)) if project.use_cases else "Sin casos de uso"),
        ("Fuentes", bool(inventoried) and not pending_sources,
         t('{v0}/{v1} sistemas inventariados', v0=len(inventoried), v1=len(project.sources)) if project.sources else "Sin sistemas"),
        ("Contexto", context_ready,
         t('{v0} documento(s) analizados', v0=len(documents)) if context_ready else t('{v0} documento(s), sin analizar', v0=len(documents))),
        ("Diagnóstico", bool(latest) and not is_stale,
         "Desactualizado" if is_stale else ("Generado" if latest else "Pendiente")),
        ("Revisión", review_status == "reviewed", ATLAS_REVIEW_LABELS.get(review_status, review_status)),
    ]
    columns = st.columns(len(steps))
    for column, (label, done, detail) in zip(columns, steps):
        with column:
            icon = ":material/check_circle:" if done else ":material/radio_button_unchecked:"
            st.markdown(t('{v0} **{v1}**', v0=icon, v1=t(label)))
            st.caption(t(detail))

    next_step = next((label for label, done, _ in steps if not done), None)
    messages = {
        "Alcance": t("Definí cliente, dominio y al menos un caso de uso en la pestaña **Alcance**."),
        "Fuentes": t("Registrá todos los sistemas del dominio y cargá su metadata en **Fuentes**."),
        "Contexto": t("Subí glosarios, KPIs o procesos y analizalos en **Contexto de negocio**."),
        "Diagnóstico": t("Generá el diagnóstico en la pestaña **Diagnóstico**."),
        "Revisión": t("Revisá brechas y registrá la decisión en **Diagnóstico**."),
    }
    if next_step:
        st.info(t('Siguiente paso: {v0}', v0=messages[next_step]), icon=":material/arrow_forward:")
    else:
        st.success(t("Diagnóstico revisado. Podés continuar en Nexo para validar el conocimiento y prepararlo para la plataforma."))


# ---------------------------------------------------------------- Alcance

def _render_scope(service: WorkbenchService, project) -> None:
    st.subheader(t("Qué se evalúa"))
    with st.form(f"atlas-scope-{project.id}"):
        columns = st.columns(4)
        client_id = columns[0].text_input(t("Cliente"), value=project.metadata.get("client_id", project.id), key='ui-atlas-_render_scope-106')
        domain_id = columns[1].text_input(t("Dominio"), value=project.metadata.get("domain_id", ""), key='ui-atlas-_render_scope-107')
        data_product_id = columns[2].text_input(
            t("Producto de datos"), value=project.metadata.get("data_product_id", project.id)
        , key='ui-atlas-_render_scope-108')
        owner = columns[3].text_input(t("Responsable del dominio"), value=project.metadata.get("owner", ""), key='ui-atlas-_render_scope-111')
        if st.form_submit_button(t("Guardar alcance"), key='ui-atlas-_render_scope-112'):
            try:
                service.update_assessment_scope(project.id, client_id, domain_id, data_product_id, owner)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.rerun()

    st.subheader(t("Casos de uso"))
    st.caption(
        t("Cada caso de uso indica qué pregunta de negocio se quiere responder y qué sistemas necesita. "
        "Atlas los usa para priorizar las brechas.")
    )
    source_names = {source.source_id: source.name for source in project.sources}
    if project.use_cases:
        st.dataframe(
            localize_rows([
                {
                    "Caso de uso": use_case.name,
                    "Pregunta de negocio": use_case.business_question,
                    "Responsable": use_case.owner,
                    "Prioridad": PRIORITY_LABELS.get(use_case.priority, use_case.priority),
                    "Sistemas": ", ".join(source_names.get(item, item) for item in use_case.source_ids),
                }
                for use_case in project.use_cases
            ]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(t("Todavía no hay casos de uso."))

    add_column, delete_column = st.columns((3, 1))
    with add_column, st.expander(t("Agregar caso de uso"), expanded=not project.use_cases):
        if not project.sources:
            st.caption(t("Tip: registrá primero los sistemas en **Fuentes** para poder vincularlos."))
        with st.form(f"atlas-use-case-{project.id}", clear_on_submit=True):
            name = st.text_input(t("Nombre"), placeholder=t("Ejemplo: Rentabilidad por cliente"), key=f"atlas-use-case-name-{project.id}")
            question = st.text_area(t("Pregunta de negocio"), placeholder=t("¿Qué clientes generan más margen?"), height=70, key='ui-atlas-_render_scope-150')
            columns = st.columns(2)
            use_case_owner = columns[0].text_input(t("Responsable"), key='ui-atlas-_render_scope-152')
            priority = columns[1].selectbox(
                t("Prioridad"), USE_CASE_PRIORITIES, index=1, format_func=option_labels(USE_CASE_PRIORITIES, dict(PRIORITY_LABELS).get)
            , key='ui-atlas-_render_scope-153')
            linked_sources = st.multiselect(
                t("Sistemas que necesita"), list(source_names), format_func=option_labels(list(source_names), source_names.get),
                key=f"atlas-use-case-sources-{project.id}",
            )
            if st.form_submit_button(t("Agregar caso de uso"), type="primary", key=f"atlas-use-case-submit-{project.id}"):
                try:
                    service.add_use_case(project.id, name, question, use_case_owner, priority, linked_sources)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    if project.use_cases:
        with delete_column, st.expander(t("Quitar")):
            use_case_names = {item.use_case_id: item.name for item in project.use_cases}
            selected = st.selectbox(
                t("Caso de uso"), list(use_case_names), format_func=option_labels(list(use_case_names), use_case_names.get),
                key=f"atlas-use-case-delete-{project.id}",
            )
            if st.button(t("Quitar caso de uso"), key=f"atlas-use-case-delete-button-{project.id}"):
                service.delete_use_case(project.id, selected)
                st.rerun()


# ---------------------------------------------------------------- Fuentes

def _render_sources(service: WorkbenchService, project) -> None:
    sources = project.sources
    inventoried = [source for source in sources if source.status == "inventoried"]
    metrics = st.columns(4)
    metrics[0].metric(t("Sistemas en alcance"), len(sources))
    metrics[1].metric(t("Inventariados"), len(inventoried))
    metrics[2].metric(t("Tablas"), sum(source.object_counts.get("tables", 0) for source in sources))
    metrics[3].metric(t("Columnas"), sum(source.object_counts.get("columns", 0) for source in sources))

    if sources:
        st.dataframe(
            localize_rows([
                {
                    "Sistema": source.name,
                    "Plataforma": t(PLATFORM_LABELS.get(source.platform, source.platform)),
                    "Estado": SOURCE_STATUS_LABELS.get(source.status, source.status),
                    "Responsable": source.owner or "Sin asignar",
                    "Acceso": ACCESS_MODE_LABELS.get(source.access_mode, source.access_mode),
                    "Tablas": source.object_counts.get("tables", 0),
                    "Columnas": source.object_counts.get("columns", 0),
                    "Archivo": source.filename,
                    "Inventariado": short_timestamp(source.inventoried_at),
                }
                for source in sources
            ]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(
            t("Registrá cada sistema que participa del dominio (ERP, lakehouse, CRM, modelos de BI, planillas). "
            "No hace falta que estén en la misma plataforma.")
        )

    register_column, load_column = st.columns(2)
    with register_column, st.container(border=True):
        st.markdown(t("**Agregar sistema**"))
        with st.form(f"atlas-source-add-{project.id}", clear_on_submit=True):
            name = st.text_input(t("Nombre"), placeholder=t("Ejemplo: ERP operativo"), key=f"atlas-source-name-{project.id}")
            platform = st.selectbox(
                t("Plataforma"), list(PLATFORM_LABELS), format_func=option_labels(list(PLATFORM_LABELS), lambda key: t(PLATFORM_LABELS[key])),
                key=f"atlas-source-platform-{project.id}",
            )
            owner = st.text_input(t("Responsable"), key=f"atlas-source-owner-{project.id}")
            description = st.text_input(t("Descripción (opcional)"), key='ui-atlas-_render_sources-225')
            if st.form_submit_button(t("Agregar sistema"), type="primary", key=f"atlas-source-submit-{project.id}"):
                try:
                    service.register_data_source(project.id, name, platform, owner, description)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()

    with load_column, st.container(border=True):
        st.markdown(t("**Cargar metadata de un sistema**"))
        if not sources:
            st.caption(t("Primero agregá un sistema."))
        else:
            source_by_id = {source.source_id: source for source in sources}
            selected_id = st.selectbox(
                t("Sistema"),
                list(source_by_id),
                format_func=option_labels(list(source_by_id), lambda item: t('{v0} · {v1}', v0=source_by_id[item].name, v1=SOURCE_STATUS_LABELS[source_by_id[item].status])),
                key=f"atlas-source-load-{project.id}",
            )
            selected = source_by_id[selected_id]
            st.caption(METADATA_FORMAT_HINTS.get(selected.platform, METADATA_FORMAT_HINTS["other"]))
            uploaded = st.file_uploader(
                t("Archivo de metadata"), type=METADATA_FILE_TYPES, key=f"atlas-source-file-{project.id}-{selected_id}"
            )
            if selected.status == "inventoried":
                st.caption(t("Volver a cargar reemplaza los objetos de este sistema; los demás no cambian."))
            if uploaded is not None and st.button(
                t("Inventariar sistema"), type="primary", key=f"atlas-source-import-{project.id}"
            ):
                try:
                    _, summary = service.import_source_metadata_file(
                        project.id, selected_id, uploaded.name, uploaded.getvalue()
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.toast(t('{v0}: {v1} tablas y {v2} columnas.', v0=selected.name, v1=summary['tables'], v2=summary['columns']))
                    st.rerun()

    _render_fabric_connector(service, project.id)
    if sources:
        _render_source_editor(service, project)
        _render_source_objects(project)


def _render_fabric_connector(service: WorkbenchService, project_id: str) -> None:
    with st.expander(t("Conexión directa a Microsoft Fabric (solo lectura)")):
        st.caption(
            t("Usa la identidad Entra configurada en el entorno. Lee solo metadata (INFORMATION_SCHEMA); "
            "no lee filas ni publica cambios.")
        )
        filter_columns = st.columns(2)
        schema_name = filter_columns[0].text_input(
            t("Schema exacto (opcional)"), placeholder="gold_sic", key=f"fabric-schema-{project_id}"
        )
        table_pattern = filter_columns[1].text_input(
            t("Filtrar tablas por nombre (opcional)"), placeholder="fact_", key=f"fabric-table-pattern-{project_id}"
        )
        action_columns = st.columns(2)
        if action_columns[0].button(t("Comprobar conexión"), key=f"fabric-check-{project_id}"):
            try:
                connection = service.check_fabric_connection()
            except Exception as exc:
                st.error(str(exc))
            else:
                st.success(t('Conexión confirmada: {v0} · {v1}', v0=connection['identity'], v1=connection['database']))
        if action_columns[1].button(t("Leer metadata"), key=f"fabric-discover-{project_id}"):
            try:
                st.session_state[f"fabric-discovery-{project_id}"] = service.discover_fabric_metadata(
                    project_id, table_pattern, schema_name
                )
            except Exception as exc:
                st.error(str(exc))
        discovery = st.session_state.get(f"fabric-discovery-{project_id}")
        if discovery:
            st.success(t('{v0} tablas/vistas y {v1} columnas leídas.', v0=len(discovery['tables']), v1=len(discovery['columns'])))
            st.dataframe(localize_rows(discovery["tables"]), width="stretch", hide_index=True, height=200)
            if st.button(t("Incorporar como sistema Fabric"), type="primary", key=f"fabric-import-{project_id}"):
                try:
                    imported = service.import_fabric_metadata(project_id, discovery)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.pop(f"fabric-discovery-{project_id}", None)
                    st.toast(t('Fabric: {v0} objetos nuevos incorporados.', v0=imported['added']))
                    st.rerun()


def _render_source_editor(service: WorkbenchService, project) -> None:
    with st.expander(t("Editar o quitar un sistema")):
        source_by_id = {source.source_id: source for source in project.sources}
        selected_id = st.selectbox(
            t("Sistema"), list(source_by_id), format_func=option_labels(list(source_by_id), lambda item: source_by_id[item].name),
            key=f"atlas-source-edit-select-{project.id}",
        )
        selected = source_by_id[selected_id]
        platforms = list(PLATFORM_LABELS)
        with st.form(f"atlas-source-edit-{project.id}-{selected_id}"):
            columns = st.columns(3)
            name = columns[0].text_input(t("Nombre"), value=selected.name, key='ui-atlas-_render_source_editor-326')
            platform = columns[1].selectbox(
                t("Plataforma"), platforms, index=platforms.index(selected.platform) if selected.platform in platforms else len(platforms) - 1,
                format_func=option_labels(platforms, lambda key: t(PLATFORM_LABELS[key])),
            key='ui-atlas-_render_source_editor-327')
            owner = columns[2].text_input(t("Responsable"), value=selected.owner, key='ui-atlas-_render_source_editor-331')
            description = st.text_input(t("Descripción"), value=selected.description, key='ui-atlas-_render_source_editor-332')
            if st.form_submit_button(t("Guardar cambios"), key='ui-atlas-_render_source_editor-333'):
                try:
                    service.update_data_source(project.id, selected_id, name, platform, owner, description)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
        confirm = st.checkbox(
            t("Quitar '{v0}' y sus objetos inventariados (se guarda un snapshot antes)", v0=selected.name),
            key=f"atlas-source-delete-confirm-{project.id}-{selected_id}",
        )
        if st.button(t("Quitar sistema"), disabled=not confirm, key=f"atlas-source-delete-{project.id}"):
            service.delete_data_source(project.id, selected_id)
            st.rerun()


def _render_source_objects(project) -> None:
    with st.expander(t("Ver objetos inventariados")):
        source_names = {source.source_id: source.name for source in project.sources}
        options = ["all", *source_names]
        selected = st.selectbox(
            t("Sistema"), options,
            format_func=option_labels(options, lambda item: "Todos" if item == "all" else source_names.get(item, item)),
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
        st.dataframe(localize_rows(rows), width="stretch", hide_index=True, height=min(400, 38 + 35 * max(len(rows), 1)))


# ---------------------------------------------------------------- Contexto

def _render_context(service: WorkbenchService, project_id: str, documents, inventory) -> None:
    settings = load_llm_settings()
    st.caption(
        t('Motor de extracción: {v0} · {v1}', v0=settings.provider, v1=settings.model)
        if settings.enabled
        else t("Motor de extracción: reglas locales (sin LLM, sin costo).")
    )
    upload_column, list_column = st.columns((2, 3))
    with upload_column, st.container(border=True):
        st.markdown(t("**Subir documentos**"))
        doc_type = st.selectbox(
            t("Tipo"), SUPPORTED_DOCUMENT_TYPES, format_func=option_labels(SUPPORTED_DOCUMENT_TYPES, lambda item: DOCUMENT_TYPE_LABELS.get(item, item)),
            key=f"atlas-doc-type-{project_id}",
        )
        uploaded_files = st.file_uploader(
            t("Glosarios, KPIs, procesos, diccionarios…"),
            type=SUPPORTED_FILE_EXTENSIONS,
            accept_multiple_files=True,
            key=f"context-files-{project_id}",
        )
        if uploaded_files and st.button(t("Subir"), type="primary", key=f"upload-docs-{project_id}"):
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
                    st.error(t('{v0}: {v1}', v0=uploaded_file.name, v1=exc))
                else:
                    loaded += 1
            if loaded:
                st.rerun()

    with list_column:
        if not documents:
            st.info(t("Todavía no hay documentos cargados."))
        else:
            st.dataframe(
                localize_rows([
                    {
                        "Archivo": document.filename,
                        "Tipo": DOCUMENT_TYPE_LABELS.get(document.doc_type, document.doc_type),
                        "Estado": document.extraction_status,
                        "Caracteres": document.extracted_chars,
                        "Subido": short_timestamp(document.uploaded_at),
                    }
                    for document in documents
                ]),
                width="stretch",
                hide_index=True,
            )
            integrity = service.get_context_document_integrity(project_id)
            if integrity["duplicate_document_ids"]:
                st.warning(t("Hay documentos heredados con IDs duplicados; la evidencia puede no ser trazable."))
                if st.button(t("Reparar IDs y volver a extraer"), key=f"repair-doc-ids-{project_id}"):
                    service.repair_context_document_ids(project_id)
                    st.rerun()
            if st.button(t("Analizar contexto de negocio"), type="primary", key=f"scan-context-{project_id}"):
                try:
                    with st.spinner(t("Analizando documentos…")):
                        service.scan_business_context(project_id)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()

    if inventory and inventory.get("status") == "invalidated":
        st.warning(t("El análisis anterior quedó invalidado. Volvé a analizar los documentos."))
    elif inventory:
        _render_context_inventory(project_id, inventory)

    with st.expander(t("Configuración del motor LLM (técnico)")):
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
        st.caption(t("Sin proveedor configurado se usan reglas locales. Solo se envía contenido autorizado."))


def _render_context_inventory(project_id: str, inventory: dict[str, object]) -> None:
    st.subheader(t("Resultado del análisis"))
    views = {
        "definitions": ("Definiciones", lambda item: {"Término": item.get("term"), "Definición": item.get("definition")}),
        "kpis": ("KPIs", lambda item: {"KPI": item.get("name") or item.get("text")}),
        "business_rules": ("Reglas", lambda item: {"Regla": item.get("text") or item.get("rule")}),
        "candidate_entities": ("Entidades vinculadas", lambda item: {"Término": item.get("term"), "Objeto técnico": item.get("matched_semantic_object")}),
        "questions_for_workshop": ("Preguntas para taller", lambda item: {"Pregunta": item.get("question")}),
    }
    counts = {key: len(inventory.get(key, []) or []) for key in views}
    selected = st.segmented_control(
        t("Ver"),
        list(views),
        format_func=option_labels(list(views), lambda key: t('{v0} ({v1})', v0=t(views[key][0]), v1=counts[key])),
        default="definitions",
        key=f"atlas-context-view-{project_id}",
        label_visibility="collapsed",
    ) or "definitions"
    if inventory.get("scanner_warning"):
        st.warning(str(inventory["scanner_warning"]))
    label, to_row = views[selected]
    items = [item for item in inventory.get(selected, []) or [] if isinstance(item, dict)]
    if not items:
        st.caption(t('No se detectaron {v0}.', v0=t(label).lower()))
        return
    rows = []
    for item in items:
        row = to_row(item)
        row["Documento"] = item.get("source_filename") or item.get("source_document_id", "")
        row["Estado"] = item.get("status", "")
        rows.append(row)
    st.dataframe(localize_rows(rows), width="stretch", hide_index=True)


# ---------------------------------------------------------------- Diagnóstico

def _render_diagnosis(service: WorkbenchService, project, assessments: list[dict[str, object]]) -> None:
    client_id = project.metadata.get("client_id", project.id)
    domain_id = project.metadata.get("domain_id", "default")
    data_product_id = project.metadata.get("data_product_id", project.id)
    action_column, info_column = st.columns((1, 3))
    if action_column.button(t("Generar diagnóstico"), type="primary", key=f"atlas-generate-{project.id}"):
        try:
            with st.spinner(t("Generando diagnóstico…")):
                service.create_atlas_assessment(project.id, client_id, domain_id, data_product_id)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state[f"atlas-select-latest-{project.id}"] = True
            st.rerun()
    info_column.caption(
        t('Cliente **{v0}** · Dominio **{v1}** · Producto de datos **{v2}**. El diagnóstico es determinista (sin LLM) y no aprueba una ontología ni publica en sistemas externos.', v0=client_id, v1=domain_id, v2=data_product_id)
    )
    settings = load_llm_settings()
    with st.expander(t("Contraste semántico")):
        st.caption(t('Proveedor: {v0} · Modelo: {v1} · Política: {v2}', v0=settings.provider, v1=settings.deployment or settings.model or '-', v2=settings.data_policy))
        if not settings.enabled:
            st.warning(t("Proveedor no habilitado o bloqueado por la política de datos. No habrá fallback heurístico."))
        max_calls = st.number_input(t("Límite de llamadas"), min_value=1, max_value=200, value=40,
                                    key=f"atlas-semantic-budget-{project.id}")
        if st.button(t("Evaluar cobertura con LLM"), icon=":material/psychology:",
                     key=f"atlas-semantic-evaluate-{project.id}"):
            try:
                with st.spinner(t("Contrastando universo y evidencia…")):
                    service.create_semantic_atlas_assessment(project.id, client_id, domain_id, data_product_id,
                                                            max_calls=int(max_calls))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state[f"atlas-select-latest-{project.id}"] = True
                st.session_state[f"atlas-diagnosis-view-{project.id}"] = "Cobertura explicativa"
                st.rerun()
    if not assessments:
        st.info(t("Todavía no hay diagnósticos para este proyecto."))
        return
    if str(assessments[0].get("created_at", "")) < project.updated_at:
        st.warning(t("Hubo cambios en el proyecto después del último diagnóstico. Conviene generarlo de nuevo."))

    runs = {str(item["run_id"]): item for item in assessments}
    if st.session_state.pop(f"atlas-select-latest-{project.id}", False):
        st.session_state[f"atlas-run-{project.id}"] = next(iter(runs))
    run_id = st.selectbox(
        t("Diagnóstico"),
        list(runs),
        format_func=option_labels(list(runs), lambda item: _run_label(runs[item])),
        key=f"atlas-run-{project.id}",
    )
    details = service.get_atlas_assessment(project.id, run_id)
    score = dict(details["readiness_score"])
    gaps = list(details["gap_backlog"])
    source_inventory = dict(details["source_inventory"])

    headline = st.columns(4)
    headline[0].metric(t("Puntaje basal"), t('{v0} / 5', v0=score.get('overall_score', 0)))
    headline[1].metric(t("Lectura"), INTERPRETATION_LABELS.get(str(score.get("interpretation")), "-"))
    headline[2].metric(t("Brechas"), len(gaps), t('{v0} altas', v0=sum(gap['severity'] == 'high' for gap in gaps)), delta_color="off")
    headline[3].metric(t("Sistemas inventariados"), dict(source_inventory.get("summary", {})).get("technical_sources", 0))

    dimension_columns = st.columns(len(score.get("dimensions", [])) or 1)
    for column, dimension in zip(dimension_columns, score.get("dimensions", [])):
        with column:
            label = DIMENSION_LABELS.get(dimension["dimension"], dimension["dimension"])
            st.progress(dimension["score"] / dimension["max_score"], text=t('{v0}: {v1}/5', v0=label, v1=dimension['score']))
            st.caption(t(dimension["evidence"]))

    views = ["Universo evaluable", "Cobertura explicativa", "Comparación", "Brechas", "Mapa entre sistemas", "Sistemas", "Informe"]
    view = st.segmented_control(
        t("Vista"), views, default=None if f"atlas-diagnosis-view-{project.id}" in st.session_state else "Brechas",
        key=f"atlas-diagnosis-view-{project.id}", label_visibility="collapsed"
    , format_func=option_labels(views, t)) or "Brechas"
    if view == "Universo evaluable":
        _render_explanatory_scope(service, project, dict(details.get("explanatory_scope", {})), run_id)
    elif view == "Cobertura explicativa":
        _render_explanatory_coverage(dict(details.get("explanatory_coverage", {})), project.id,
                                     dict(details.get("explanatory_diagnosis", {})))
    elif view == "Comparación":
        _render_explanatory_comparison(service, project.id, runs, run_id, details)
    elif view == "Brechas":
        _render_gaps(project, gaps)
    elif view == "Mapa entre sistemas":
        _render_cross_source_map(dict(details.get("cross_source_map", {})))
    elif view == "Sistemas":
        _render_assessed_sources(source_inventory)
    else:
        st.download_button(
            t("Descargar informe (Markdown)"),
            data=str(details["execution_summary"]),
            file_name=f"atlas-{run_id}.md",
            mime="text/markdown",
            key=f"atlas-report-{run_id}",
        )
        with st.container(height=500, border=True):
            st.markdown(str(details["execution_summary"]))
        st.caption(t('Paquete local: {v0}', v0=details['package_path']))

    _render_review(service, project.id, run_id, dict(details.get("assessment_review", {})))


def _render_explanatory_comparison(service, project_id: str, runs: dict, run_id: str, details: dict) -> None:
    import json
    from ontology_workbench.explanatory_coverage import compare_explanatory_assessments

    st.subheader(t("Comparación de assessments"))
    choices = {key: value for key, value in runs.items() if key != run_id}
    if not choices:
        st.info(t("Se necesitan dos diagnósticos para comparar."))
        return
    key = f"atlas-compare-before-{project_id}"
    if st.session_state.get(key) not in choices:
        st.session_state[key] = next(iter(choices))
    previous_id = st.selectbox(t("Assessment inicial"), list(choices), format_func=option_labels(list(choices), lambda value: _run_label(choices[value])), key=key)
    before = service.get_atlas_assessment(project_id, previous_id)
    comparison = compare_explanatory_assessments(before, details)
    if not comparison["available"]:
        st.info(t(comparison["reason"]))
        return
    st.caption(t('Inicial: {v0} · Final: {v1}', v0=previous_id, v1=run_id))
    st.caption(t(comparison["warning"]))
    if comparison["scope_changed"]:
        st.warning(t("Cambió el alcance o sus criterios. Los porcentajes tienen bases distintas; no se calcula una diferencia de avance."))
    else:
        st.caption(t("Mismo alcance y criterios: porcentajes comparables. Completar un análisis no equivale a resolver una falta documental."))
    for limitation in comparison["limitations"]:
        st.warning(t(limitation))
    labels = {"entity": t("Entidades"), "relationship": t("Relaciones"), "kpi": "KPIs", "property": t("Propiedades")}
    columns = st.columns(4)
    for column, (kind, label) in zip(columns, labels.items()):
        group = comparison["groups"][kind]
        values = []
        for side in ("before", "after"):
            percent = group[f"{side}_percent"]
            values.append(t("No evaluable") if not group[f"{side}_denominator"] else t("Sin evaluar") if percent is None else f"{percent:g}%")
        delta = group["delta_percentage_points"]
        column.markdown(t('**{v0}**\n\nInicial: **{v1}**  \nFinal: **{v2}**', v0=label, v1=values[0], v2=values[1]))
        if delta is not None:
            column.caption(t('Diferencia: {v0:+g} pp', v0=delta))
        column.caption(t('En alcance: {v0} → {v1}', v0=group['before_denominator'], v1=group['after_denominator']))
    changes = {"added": t("Agregado"), "included": t("Incluido"), "removed": t("Retirado"), "excluded": t("Excluido"),
               "analysis_completed": t("Análisis completado"), "classification_changed": t("Clasificación cambió"),
               "aspects_changed": t("Aspectos cambiaron"), "evidence_changed": t("Evidencia cambió"), "unchanged": t("Sin cambios")}
    statuses = {"explained": t("Explicado"), "partial": t("Parcial"), "unexplained": t("Sin explicación"), "contradictory": t("Contradictorio"),
                "failed": t("Fallo de evaluación"), "not_evaluated": t("Sin evaluar"), "excluded": t("Excluido"), None: t("No inventariado")}
    only_changes = st.checkbox(t("Sólo cambios"), value=True, key=f"atlas-compare-changes-{project_id}")
    rows = [row for row in comparison["transitions"] if not only_changes or row["change"] != "unchanged"]
    if rows:
        st.dataframe(localize_rows([{"Elemento": row["name"], "Grupo": labels[row["kind"]], "Cambio": changes[row["change"]],
                       "Inicial": statuses[row["before_state"]], "Final": statuses[row["after_state"]],
                       "Evidencias nuevas": len(row["new_evidence"]), "Faltantes finales": ", ".join(t(aspect) for aspect in row["missing_after"]),
                       "Motivo": reason_text(row["reason"])} for row in rows]), hide_index=True, width="stretch")
        options = {row["element_id"]: row for row in rows}
        key = f"atlas-compare-element-{project_id}"
        if st.session_state.get(key) not in options:
            st.session_state[key] = next(iter(options))
        selected = st.selectbox(t("Transición para revisar"), list(options),
            format_func=option_labels(list(options), lambda value: t('{v0} · {v1} · {v2}', v0=options[value]['name'], v1=changes[options[value]['change']], v2=value)), key=key)
        row = options[selected]
        st.text(reason_text(row["reason"]))
        for column, title, package in zip(st.columns(2), ("Evidencia inicial", "Evidencia final"), (before, details)):
            with column:
                st.markdown(f"**{t(title)}**")
                element = next((item for item in package["explanatory_coverage"]["elements"] if item["element_id"] == selected), None)
                for claim in (element["evidence"] + element["contradictions"]) if element else []:
                    st.caption(t('{v0} · {v1}', v0=t(claim.get('aspect', 'Contradicción')), v1=claim['chunk_id']))
                    st.text(claim["quote"])
    else:
        st.info(t("Sin cambios en clasificaciones, aspectos o evidencia citada."))
    st.subheader(t("Resultados de pedidos anteriores"))
    outcomes = {"open": t("Abierto"), "out_of_scope": t("Fuera de alcance, no resuelto"), "analysis_completed": t("Análisis completado"),
                "review_closure": t("Revisar cierre")}
    requests = comparison["request_outcomes"]
    if requests:
        st.dataframe(localize_rows([{"Pedido": item["request_id"], "Elemento": item["element_name"], "Resultado": outcomes[item["outcome"]],
                       "Criterio de cierre": t(item["closure_criterion"]), "Pedidos actuales": ", ".join(item["current_request_ids"])}
                      for item in requests]), hide_index=True, width="stretch")
    else:
        st.caption(t("El assessment inicial no conserva pedidos."))
    st.download_button(t("Descargar comparación"), json.dumps(comparison, ensure_ascii=False, indent=2),
                       file_name=f"{project_id}-comparison.json", mime="application/json", icon=":material/download:", key='ui-atlas-_render_explanatory_comparison-690')


def _render_explanatory_coverage(coverage: dict, project_id: str, diagnosis: dict | None = None) -> None:
    import json

    if not coverage:
        st.info(t("Este diagnóstico es anterior a la matriz explicativa. Generá uno nuevo."))
        return
    labels = {"entity": t("Entidades"), "relationship": t("Relaciones"), "kpi": "KPIs", "property": t("Propiedades")}
    states = {"explained": t("Explicado"), "partial": t("Parcial"), "unexplained": t("Sin explicación"),
              "contradictory": t("Contradictorio")}
    st.subheader(t("Cobertura explicativa"))
    analysis = coverage.get("analysis")
    if analysis:
        status_labels = {"complete": t("Análisis completo"), "partial_failure": t("Análisis con fallos"),
                         "blocked_by_policy": t("Bloqueado por política"), "provider_unavailable": t("Proveedor no habilitado"),
                         "no_scope": t("Sin universo evaluable"), "no_evidence": t("Sin evidencia documental")}
        st.caption(t('{v0} · Modo: {v1} · Proveedor: {v2} · Modelo: {v3} · Prompt: {v4}', v0=status_labels.get(analysis['status'], analysis['status']), v1=analysis['effective_mode'], v2=analysis['configuration']['provider'], v3=analysis['configuration']['model'] or '-', v4=analysis['prompt_version']))
        st.caption(t('Llamadas: {v0} / {v1} · Reutilizado: {v2}', v0=analysis['calls_made'], v1=analysis['max_calls'], v2=t('Sí' if analysis['cache_reused'] else 'No')))
        if analysis["status"] != "complete":
            st.warning(t("El contraste no se completó. Los pendientes y fallos no son evidencia de ausencia de explicación."))
        if analysis["calls"]:
            with st.expander(t("Procesamiento del contraste")):
                st.dataframe(localize_rows(analysis["calls"]), hide_index=True, width="stretch")
        st.caption(t("Propuestas del LLM pendientes de revisión humana; no equivalen a aprobación en Nexo."))
        if analysis["human_review_sample"]:
            st.text(t("Muestra para revisión: ") + ", ".join(analysis["human_review_sample"]))
    st.html("<style>.st-key-atlas-coverage-metrics [data-testid='stMetricValue'] "
            "{font-size:1.35rem;white-space:normal;min-height:2rem;}"
            ".st-key-atlas-coverage-metrics [data-testid='stMetricValue'] * "
            "{white-space:normal;overflow:visible;text-overflow:clip;}</style>")
    with st.container(key="atlas-coverage-metrics"):
        for column, (kind, label) in zip(st.columns(4), labels.items()):
            group = coverage["groups"][kind]
            percent = group["explained_percent"]
            value = "No evaluable" if not group["denominator"] else "Sin evaluar" if percent is None else f"{percent:g}%"
            column.metric(label, t(value))
            column.caption(t('{v0} explicados / {v1} en alcance · {v2} evaluados · {v3} fallos', v0=group['counts']['explained'], v1=group['denominator'], v2=group['evaluated'], v3=group['failed']))
    for limitation in coverage["limitations"]:
        st.warning(t(limitation))
    st.caption(t(coverage["validation_boundary"]))
    if coverage.get("inferred_explanations"):
        st.caption(t("{v0} explicaciones inferidas por el modelo; no cuentan como cobertura documental.",
                     v0=len(coverage["inferred_explanations"])))
    st.caption(t('Alcance: {v0} · Cálculo: {v1}', v0=coverage['scope_version'], v1=coverage['calculation_version']))
    st.download_button(t("Descargar matriz"), json.dumps(coverage, ensure_ascii=False, indent=2),
                       file_name=f"{project_id}-coverage.json", mime="application/json", icon=":material/download:", key='ui-atlas-_render_explanatory_coverage-733')
    kind = st.selectbox(t("Grupo de cobertura"), list(labels), format_func=option_labels(list(labels), labels.get),
                        key=f"atlas-coverage-kind-{project_id}")
    elements = [row for row in coverage["elements"] if row["kind"] == kind and row["included"]]
    group = coverage["groups"][kind]
    st.dataframe(localize_rows([{"Estado": label, "Elementos": group["counts"][state],
                   "% del alcance": group["state_percentages"][state]}
                  for state, label in states.items()]), hide_index=True, width="stretch")
    if diagnosis:
        st.caption(t(diagnosis["use_case_link_warning"]))
        dimensions = []
        for dimension, entries in (("Sistema", diagnosis["systems"]), ("Caso de uso (por sistema)", diagnosis["use_cases"])):
            for entry in entries:
                summary = entry["groups"][kind]
                percent = summary["explained_percent"]
                value = "No evaluable" if not summary["denominator"] else "Sin evaluar" if percent is None else f"{percent:g}%"
                dimensions.append({"Dimensión": t(dimension), "Nombre": entry["name"], "Cobertura": t(value),
                                   "En alcance": summary["denominator"], "Evaluados": summary["evaluated"],
                                   "Fallos": summary["failed"]})
        if dimensions:
            st.dataframe(localize_rows(dimensions), hide_index=True, width="stretch")
        source_names = {entry["source_id"]: entry["name"] for entry in diagnosis["systems"]}
        case_names = {entry["use_case_id"]: entry["name"] for entry in diagnosis["use_cases"]}
        filter_columns = st.columns(2)
        source_filter = filter_columns[0].selectbox(t("Sistema de cobertura"), [None, *source_names],
            format_func=option_labels([None, *source_names], lambda key: t("Todos") if key is None else source_names[key]), key=f"atlas-coverage-source-{project_id}")
        case_filter = filter_columns[1].selectbox(t("Caso de uso de cobertura"), [None, *case_names],
            format_func=option_labels([None, *case_names], lambda key: t("Todos") if key is None else case_names[key]), key=f"atlas-coverage-case-{project_id}")
        status_labels = {**states, "not_evaluated": t("Sin evaluar"), "failed": t("Fallo de evaluación")}
        statuses = st.multiselect(t("Estados de cobertura"), list(status_labels), format_func=option_labels(list(status_labels), status_labels.get),
                                  key=f"atlas-coverage-status-{project_id}")
        from ontology_workbench.explanatory_coverage import ASPECT_LABELS
        from ontology_workbench.explanatory_scope import ASPECTS

        aspects = st.multiselect(t("Aspectos faltantes"), ASPECTS[kind], format_func=option_labels(ASPECTS[kind], lambda key: t(ASPECT_LABELS.get(key, key))),
                                 key=f"atlas-coverage-aspects-{project_id}-{kind}")
        elements = [row for row in elements if (source_filter is None or source_filter in row["source_ids"])
                    and (case_filter is None or case_filter in row["use_case_ids"])
                    and (not statuses or (row["state"] or row["evaluation_status"]) in statuses)
                    and (not aspects or set(aspects) & set(row["missing_aspects"]))]
        st.caption(t('Elementos visibles: {v0} / {v1} en alcance. Los filtros no cambian el denominador.', v0=len(elements), v1=group['denominator']))
        _render_information_requests(diagnosis, {row["element_id"] for row in elements}, project_id, kind)
    if not elements:
        st.info(t("Grupo sin elementos en alcance: no evaluable." if not group["denominator"] else "Sin elementos para estos filtros."))
        return
    options = {row["element_id"]: row for row in elements}
    st.dataframe(localize_rows([{"Elemento": row["name"], "Estado": states.get(row["state"],
                   t("Fallo de evaluación" if row["evaluation_status"] == "failed" else "Sin evaluar")),
                   "Método": row["method"], "Motivo": reason_text(row["reason"]),
                   "Aspectos faltantes": ", ".join(t(aspect) for aspect in row["missing_aspects"]), "ID": row["element_id"]}
                  for row in elements]), hide_index=True, width="stretch")
    element_key = f"atlas-coverage-element-{project_id}-{kind}"
    if st.session_state.get(element_key) not in options:
        st.session_state[element_key] = next(iter(options))
    selected = st.selectbox(t("Elemento de cobertura"), list(options),
                            format_func=option_labels(list(options), lambda key: t('{v0} · {v1}', v0=options[key]['name'], v1=key)),
                            key=element_key)
    row = options[selected]
    st.caption(t('Respaldados: {v0} · Faltantes: {v1}', v0=', '.join(t(aspect) for aspect in row['supported_aspects']) or '-', v1=', '.join(t(aspect) for aspect in row['missing_aspects']) or '-'))
    for citation in row["evidence"]:
        st.text(t('{v0} · {v1} · {v2}', v0=t(citation['aspect']), v1=citation.get('filename') or '-', v2=citation['chunk_id']))
        st.text(citation["quote"])
    for contradiction in row["contradictions"]:
        st.warning(contradiction["reason"])
        st.text(t('{v0} · {v1}', v0=contradiction.get('filename') or '-', v1=contradiction['chunk_id']))
        st.text(contradiction["quote"])
    for error in row["validation_errors"]:
        st.error(t(error))
    for inference in coverage.get("inferred_explanations", []):
        if inference["element_id"] != selected:
            continue
        with st.expander(t("Explicacion inferida: {aspect}", aspect=t(inference["aspect"]))):
            st.warning(t("Inferida en grado importante por el modelo. No confirmada documentalmente; requiere revision humana."))
            st.text(inference["explanation"])
            st.markdown(t("**Fundamento de la inferencia**"))
            st.text(inference["basis"])
            st.markdown(t("**Supuestos por confirmar**"))
            for assumption in inference["assumptions"]:
                st.text(assumption)
            st.markdown(t("**Validaciones pendientes**"))
            for validation in inference["validation_needed"]:
                st.text(validation)
            for citation in inference["related_evidence"]:
                st.caption(t("Contexto que motivo la hipotesis, no prueba: {chunk_id}", chunk_id=citation["chunk_id"]))
                st.text(citation["quote"])


def _render_information_requests(diagnosis: dict, visible_ids: set, project_id: str, kind: str) -> None:
    import json

    st.subheader(t("Pedidos de información"))
    requests = [request for request in diagnosis["requests"] if request["element_id"] in visible_ids]
    actions = {"evaluate": t("Completar análisis"), "retry_analysis": t("Reintentar análisis"),
               "request_evidence": t("Solicitar documentación"), "resolve_contradiction": t("Resolver contradicción")}
    if not requests:
        st.info(t("Sin pedidos abiertos para esta selección."))
        return
    st.dataframe(localize_rows([{"Elemento": item["element_name"], "Acción": actions[item["action"]],
                   "Prioridad": t(item["priority"]), "Responsable propuesto": item["proposed_owner"],
                   "Pedido": request_text(item), "Criterio de cierre": t(item["closure_criterion"])}
                  for item in requests]), hide_index=True, width="stretch")
    st.download_button(t("Descargar pedidos"), json.dumps(requests, ensure_ascii=False, indent=2),
                       file_name=f"{project_id}-requests.json", mime="application/json", icon=":material/download:", key='ui-atlas-_render_information_requests-819')
    options = {item["request_id"]: item for item in requests}
    key = f"atlas-request-{project_id}-{kind}"
    if st.session_state.get(key) not in options:
        st.session_state[key] = next(iter(options))
    selected = st.selectbox(t("Pedido para revisar"), list(options),
        format_func=option_labels(list(options), lambda request_id: t('{v0} · {v1} · {v2}', v0=options[request_id]['element_name'], v1=actions[options[request_id]['action']], v2=request_id)), key=key)
    request = options[selected]
    st.text(request_text(request))
    st.caption(t('Responsable propuesto: {v0} · Por confirmar · Prioridad: {v1}', v0=request['proposed_owner'], v1=t(request['priority'])))
    st.text(t("Criterio de cierre: ") + t(request["closure_criterion"]))
    st.text(t("Motivo: ") + reason_text(request["reason"]))


def _render_explanatory_scope(service, project, scope, run_id) -> None:
    import json

    from ontology_workbench.explanatory_scope import SCOPE_KEY, build_explanatory_scope

    if not scope:
        st.info(t("Este diagnóstico es anterior al universo evaluable. Generá uno nuevo."))
        return
    labels = {"entity": t("Entidades"), "relationship": t("Relaciones"), "kpi": "KPIs", "property": t("Propiedades")}
    st.subheader(t("Universo evaluable"))
    columns = st.columns(4)
    for column, (kind, label) in zip(columns, labels.items()):
        group = scope["groups"][kind]
        column.metric(label, t('{v0} / {v1}', v0=group['included'], v1=group['total']) if group["total"] else t("No evaluable"))
    for limitation in scope["limitations"]:
        st.warning(t(limitation))
    st.caption(t(scope["use_case_link_warning"]))
    st.caption(t('Alcance: {v0} · Criterios: {v1} · Sin evaluación explicativa todavía.', v0=scope['scope_version'], v1=scope['criteria_version']))
    kind = st.selectbox(t("Grupo de elementos"), list(labels), format_func=option_labels(list(labels), labels.get), key=f"atlas-universe-kind-{project.id}")
    elements = [item for item in scope["elements"] if item["kind"] == kind]
    if not elements:
        st.info(t("Grupo sin elementos: no evaluable."))
        return
    st.dataframe(localize_rows([
        {"Elemento": item["name"], "Sistemas": ", ".join(item["source_names"]),
         "En alcance": item["included"], "Motivo": item["scope_reason"],
         "Casos de uso (por sistema)": ", ".join(item["use_case_ids"]),
         "Aspectos a explicar": ", ".join(t(aspect) for aspect in item["required_aspects"]), "ID estable": item["element_id"]}
        for item in elements
    ]), hide_index=True, width="stretch")
    if scope["scope_version"] != build_explanatory_scope(project)["scope_version"]:
        st.info(t("Este universo difiere del proyecto actual. Seleccioná el diagnóstico actualizado o generá uno nuevo para ajustar el alcance."))
        return
    options = {item["element_id"]: item for item in elements}
    selected = st.selectbox(t("Elemento para ajustar alcance"), list(options),
                            format_func=option_labels(list(options), lambda key: t('{v0} · {v1}', v0=options[key]['name'], v1=', '.join(options[key]['source_names']))),
                            key=f"atlas-universe-element-{project.id}-{kind}")
    item = options[selected]
    with st.form(f"atlas-universe-form-{run_id}-{selected}"):
        included = st.checkbox(t("Incluir en el universo"), value=item["included"], key='ui-atlas-_render_explanatory_scope-873')
        reason = st.text_input(t("Motivo del ajuste (obligatorio al excluir)"), value=item["scope_reason"], key='ui-atlas-_render_explanatory_scope-874')
        if st.form_submit_button(t("Guardar alcance y generar diagnóstico"), key='ui-atlas-_render_explanatory_scope-875'):
            if not included and not reason.strip():
                st.error(t("Indicá un motivo para excluir el elemento."))
            else:
                decisions = json.loads(project.metadata.get(SCOPE_KEY, "{}"))
                decisions[selected] = {"included": included, "reason": reason.strip()}
                service.update_metadata(project.id, {SCOPE_KEY: json.dumps(decisions)})
                service.create_atlas_assessment(project.id, project.metadata.get("client_id", project.id),
                                               project.metadata.get("domain_id", "default"),
                                               project.metadata.get("data_product_id", project.id))
                st.session_state[f"atlas-select-latest-{project.id}"] = True
                st.rerun()


def _run_label(assessment: dict[str, object]) -> str:
    summary = dict(assessment.get("summary", {}))
    review = dict(assessment.get("assessment_review", {}))
    parts = [short_timestamp(assessment.get("created_at"))]
    if summary:
        parts.append(t('{v0}/5 · {v1} brechas', v0=summary.get('overall_score'), v1=summary.get('gaps')))
    parts.append(ATLAS_REVIEW_LABELS.get(str(review.get("status", "pending_review")), "-"))
    parts.append(str(assessment["run_id"]))
    return " · ".join(parts)


def _render_gaps(project, gaps: list[dict[str, object]]) -> None:
    if not gaps:
        st.success(t("No se detectaron brechas con las reglas basales. Igual hace falta revisión funcional."))
        return
    source_names = {source.source_id: source.name for source in project.sources}
    use_case_names = {use_case.use_case_id: use_case.name for use_case in project.use_cases}
    filter_columns = st.columns(2)
    severities = filter_columns[0].multiselect(
        t("Severidad"), list(SEVERITY_LABELS), default=list(SEVERITY_LABELS),
        format_func=option_labels(list(SEVERITY_LABELS), dict(SEVERITY_LABELS).get), key=f"atlas-gap-severity-{project.id}",
    )
    categories = sorted({str(gap.get("category", "gobierno")) for gap in gaps})
    selected_categories = filter_columns[1].multiselect(
        t("Categoría"), categories, default=categories,
        format_func=option_labels(categories, lambda item: GAP_CATEGORY_LABELS.get(item, item)), key=f"atlas-gap-category-{project.id}",
    )
    visible = sorted(
        (
            gap for gap in gaps
            if gap["severity"] in severities and str(gap.get("category", "gobierno")) in selected_categories
        ),
        key=lambda gap: SEVERITY_ORDER.get(str(gap["severity"]), 9),
    )
    st.dataframe(
        localize_rows([
            {
                "Severidad": SEVERITY_LABELS.get(str(gap["severity"]), gap["severity"]),
                "Categoría": GAP_CATEGORY_LABELS.get(str(gap.get("category")), gap.get("category", "")),
                "Sistema": source_names.get(str(gap.get("source_id", "")), gap.get("source_id", "")),
                "Casos de uso": ", ".join(use_case_names.get(item, item) for item in gap.get("use_case_ids", [])),
                "Hallazgo": gap["message"],
                "Acción sugerida": gap["recommendation"],
            }
            for gap in visible
        ]),
        width="stretch",
        hide_index=True,
        column_config={
            "Hallazgo": st.column_config.TextColumn(width="large"),
            "Acción sugerida": st.column_config.TextColumn(width="large"),
        },
    )


def _render_cross_source_map(cross_source_map: dict[str, object]) -> None:
    if not cross_source_map:
        st.info(t("Este diagnóstico se generó antes del mapa entre sistemas. Generá uno nuevo."))
        return
    summary = dict(cross_source_map.get("summary", {}))
    if summary.get("sources", 0) < 2:
        st.info(t("Se necesitan al menos dos sistemas inventariados para comparar entidades entre ellos."))
        return
    metrics = st.columns(3)
    metrics[0].metric(t("Entidades detectadas"), summary.get("entities", 0))
    metrics[1].metric(t("En más de un sistema"), summary.get("shared_entities", 0))
    metrics[2].metric(t("Con clave común"), summary.get("shared_with_common_key", 0))
    st.caption(str(cross_source_map.get("warning", "")))
    shared = list(cross_source_map.get("shared_entities", []))
    if shared:
        st.dataframe(
            localize_rows([
                {
                    "Entidad": row["entity"],
                    "Sistemas": ", ".join(row["sources"]),
                    "Tablas": " | ".join(", ".join(tables) for tables in dict(row["tables"]).values()),
                    "Clave común": row.get("common_key") or "No identificada",
                    "Columnas clave": " | ".join(", ".join(cols) for cols in dict(row.get("key_columns", {})).values()),
                    "Otras claves compartidas": ", ".join(row.get("shared_reference_keys", [])),
                }
                for row in shared
            ]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.warning(t("Ninguna entidad aparece en más de un sistema con un nombre reconocible."))
    single = list(cross_source_map.get("single_source_entities", []))
    if single:
        with st.expander(t('Entidades presentes en un solo sistema ({v0})', v0=len(single))):
            st.dataframe(
                localize_rows([
                    {"Entidad": row["entity"], "Sistema": ", ".join(row["sources"]),
                     "Tablas": ", ".join(t for tables in dict(row["tables"]).values() for t in tables)}
                    for row in single
                ]),
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
    st.markdown(t("**Sistemas técnicos**"))
    st.dataframe(localize_rows(rows), width="stretch", hide_index=True)
    documents = list(source_inventory.get("sources", []))
    if documents:
        st.markdown(t("**Documentos**"))
        st.dataframe(
            localize_rows([
                {
                    "Archivo": item["filename"],
                    "Tipo": DOCUMENT_TYPE_LABELS.get(item["document_type"], item["document_type"]),
                    "Estado": item["extraction_status"],
                    "SHA-256": str(item["content_sha256"])[:12],
                }
                for item in documents
            ]),
            width="stretch",
            hide_index=True,
        )


def _render_review(service: WorkbenchService, project_id: str, run_id: str, review: dict[str, object]) -> None:
    if not review:
        return
    with st.container(border=True):
        st.markdown(t("**Revisión del diagnóstico**"))
        st.caption(t("Registra la decisión humana sobre este diagnóstico. No aprueba una ontología."))
        with st.form(f"atlas-review-{run_id}"):
            columns = st.columns(3)
            options = list(ATLAS_REVIEW_LABELS)
            current = str(review.get("status", "pending_review"))
            status = columns[0].selectbox(
                t("Decisión"), options, index=options.index(current) if current in options else 0,
                format_func=option_labels(options, dict(ATLAS_REVIEW_LABELS).get),
            key='ui-atlas-_render_review-1038')
            reviewer_name = columns[1].text_input(t("Revisor/a"), value=str(review.get("reviewer") or reviewer()[0]), key='ui-atlas-_render_review-1042')
            reviewer_role = columns[2].text_input(t("Rol"), value=str(review.get("reviewer_role") or reviewer()[1]), key='ui-atlas-_render_review-1043')
            note = st.text_area(t("Nota"), value=str(review.get("note", "")), height=80, key='ui-atlas-_render_review-1044')
            if st.form_submit_button(t("Guardar revisión"), key='ui-atlas-_render_review-1045'):
                try:
                    service.update_atlas_review(project_id, run_id, status, reviewer_name, reviewer_role, note)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
