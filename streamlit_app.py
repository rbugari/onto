from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
DATA_DIR = Path(os.environ.get("ONTO_DATA_DIR", ROOT_DIR / "data"))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore
from onto_ui.argos import render_argos
from onto_ui.atlas import render_atlas
from onto_ui.common import render_reviewer_identity
from onto_ui.nexo import render_nexo
from onto_ui.i18n import LocalizedLabels, localize_rows, option_labels, render_language_selector, t


store = ProjectStore(DATA_DIR / "projects")
service = WorkbenchService(store)


PRODUCT_AREAS = {
    "Atlas": "Atlas",
    "Nexo": "Nexo",
    "Argos": "Argos",
}

PRODUCT_STAGE_LABELS = LocalizedLabels({
    "Atlas": "1. Atlas · Diagnóstico",
    "Nexo": "2. Nexo · Validar conocimiento",
    "Argos": "3. Argos · Investigar el negocio",
})


def render_project_selector() -> str | None:
    projects = service.list_projects()
    if not projects:
        st.sidebar.info(t("No hay proyectos todavia. Crea uno para empezar."))
        return None

    labels = {project.id: project.name for project in projects}
    current_id = st.session_state.get("selected_project_id")
    selected_index = list(labels.keys()).index(current_id) if current_id in labels else 0
    selected_id = st.sidebar.selectbox(
        t("Proyecto"),
        options=list(labels.keys()),
        index=selected_index,
        format_func=option_labels(list(labels.keys()), lambda item: labels[item]),
        key="project-selector",
    )
    if selected_id != current_id:
        st.session_state["selected_project_id"] = selected_id
        st.session_state["project_context_ready"] = False
        st.session_state["project_context_project_id"] = None
        st.session_state["active_product_area"] = "Atlas"
    return selected_id


def render_create_project() -> None:
    with st.sidebar.expander(t("Crear proyecto")):
        with st.form("create-project", clear_on_submit=True):
            project_name = st.text_input(t("Nombre"), key='ui-streamlit_app-render_create_project-72')
            project_description = st.text_area(t("Descripcion"), key='ui-streamlit_app-render_create_project-73')
            submitted = st.form_submit_button(t("Crear proyecto"), key='ui-streamlit_app-render_create_project-74')
            if submitted:
                try:
                    project = service.create_project(project_name, project_description)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["selected_project_id"] = project.id
                    st.session_state["project_context_ready"] = False
                    st.session_state["project_context_project_id"] = None
                    st.rerun()

    with st.sidebar.expander(t("Importar proyecto")):
        uploaded_file = st.file_uploader(t("Archivo JSON exportado"), type=["json"], key='ui-streamlit_app-render_create_project-87')
        preserve_project_id = st.checkbox(t("Preservar id si esta libre"), value=False, key='ui-streamlit_app-render_create_project-88')
        if uploaded_file is not None and st.button(t("Importar JSON"), key='ui-streamlit_app-render_create_project-89'):
            try:
                payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
                project = service.import_project(payload, preserve_project_id=preserve_project_id)
            except (ValueError, json.JSONDecodeError) as exc:
                st.error(str(exc))
            else:
                st.session_state["selected_project_id"] = project.id
                st.session_state["project_context_ready"] = False
                st.session_state["project_context_project_id"] = None
                st.success(t("Proyecto importado"))
                st.rerun()


def render_project_context_gate(project) -> bool:
    if (
        st.session_state.get("project_context_ready")
        and st.session_state.get("project_context_project_id") == project.id
    ):
        return True

    st.title(t("Contexto de trabajo"))
    st.header(project.name)
    st.caption(
        t("Selecciona un proyecto para trabajar con sus datos, contexto y decisiones.")
    )

    issues = service.validate_project(project.id)
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    infos = [issue for issue in issues if issue.level == "info"]

    if errors:
        st.error(t("El proyecto no puede abrirse todavía porque tiene errores estructurales."))
        for issue in errors:
            st.error(t('{v0}: {v1}', v0=issue.code, v1=issue.message))
    else:
        st.success(t("Proyecto validado. Listo para trabajar."))
        with st.expander(t("Ver validación del proyecto")):
            st.write(t('Conceptos: {v0}', v0=len(project.concepts)))
            st.write(t('Relaciones: {v0}', v0=len(project.relations)))
            st.write(t('Avisos: {v0}', v0=len(warnings)))
            for issue in warnings:
                st.warning(t('{v0}: {v1}', v0=issue.code, v1=issue.message))
            for issue in infos:
                st.info(t('{v0}: {v1}', v0=issue.code, v1=issue.message))

    open_project = st.button(
        t("Abrir proyecto"),
        type="primary",
        disabled=bool(errors),
        width="stretch",
    key='ui-streamlit_app-render_project_context_gate-136')
    if open_project and not errors:
        st.session_state["project_context_ready"] = True
        st.session_state["project_context_project_id"] = project.id
        st.session_state["active_product_area"] = "Atlas"
        st.rerun()
    return False


def render_project_overview(project_id: str, project) -> None:
    issues = service.validate_project(project_id)
    metrics = st.columns(4)
    metrics[0].metric(t("Conceptos"), len(project.concepts))
    metrics[1].metric(t("Relaciones"), len(project.relations))
    metrics[2].metric(t("Errores"), sum(1 for issue in issues if issue.level == "error"))
    metrics[3].metric(t("Warnings"), sum(1 for issue in issues if issue.level == "warning"))

    with st.expander(t("Validacion estructural"), expanded=True):
        if not issues:
            st.success(t("No se detectaron observaciones estructurales."))
        else:
            for issue in issues:
                if issue.level == "error":
                    st.error(t('{v0}: {v1}', v0=issue.code, v1=issue.message))
                elif issue.level == "warning":
                    st.warning(t('{v0}: {v1}', v0=issue.code, v1=issue.message))
                else:
                    st.info(t('{v0}: {v1}', v0=issue.code, v1=issue.message))


def render_export_actions(project_id: str) -> None:
    st.subheader(t("Exportacion"))
    json_payload = service.export_project_json(project_id)
    markdown_payload = service.export_project_markdown(project_id)
    st.download_button(
        t("Descargar JSON"),
        data=json_payload,
        file_name=f"{project_id}.json",
        mime="application/json",
        width="stretch",
    key='ui-streamlit_app-render_export_actions-175')
    st.download_button(
        t("Descargar resumen Markdown"),
        data=markdown_payload,
        file_name=f"{project_id}.md",
        mime="text/markdown",
        width="stretch",
    key='ui-streamlit_app-render_export_actions-182')


def render_snapshots(project_id: str) -> None:
    st.subheader(t("Snapshots locales"))
    with st.form("create-snapshot", clear_on_submit=True):
        note = st.text_input(t("Nota del snapshot"), key='ui-streamlit_app-render_snapshots-194')
        submitted = st.form_submit_button(t("Crear snapshot"), key='ui-streamlit_app-render_snapshots-195')
        if submitted:
            service.create_snapshot(project_id, note=note)
            st.success(t("Snapshot generado"))
            st.rerun()

    snapshots = service.list_snapshots(project_id)
    if not snapshots:
        st.caption(t("Todavia no hay snapshots para este proyecto."))
        return

    snapshot_options = {snapshot.snapshot_id: snapshot for snapshot in snapshots}
    selected_snapshot_id = st.selectbox(
        t("Historial disponible"),
        options=list(snapshot_options.keys()),
        format_func=option_labels(list(snapshot_options.keys()), lambda item: t('{v0} | {v1}', v0=item, v1=snapshot_options[item].note or 'sin nota')),
    key='ui-streamlit_app-render_snapshots-207')
    if st.button(t("Restaurar snapshot"), key='ui-streamlit_app-render_snapshots-212'):
        service.restore_snapshot(project_id, selected_snapshot_id)
        st.success(t("Snapshot restaurado"))
        st.rerun()


def render_metadata_editor(project_id: str, metadata: dict[str, str]) -> None:
    with st.expander(t("Metadata del proyecto")):
        raw_metadata = "\n".join(f"{key}={value}" for key, value in metadata.items())
        with st.form("metadata-form"):
            metadata_blob = st.text_area(
                t("Pares clave=valor, uno por linea"),
                value=raw_metadata,
                height=140,
            key='ui-streamlit_app-render_metadata_editor-222')
            submitted = st.form_submit_button(t("Guardar metadata"), key='ui-streamlit_app-render_metadata_editor-227')
            if submitted:
                parsed: dict[str, str] = {}
                for line in metadata_blob.splitlines():
                    if not line.strip():
                        continue
                    key, separator, value = line.partition("=")
                    if not separator:
                        st.error(t('Linea invalida: {v0}', v0=line))
                        return
                    parsed[key.strip()] = value.strip()
                service.update_metadata(project_id, parsed)
                st.success(t("Metadata actualizada"))
                st.rerun()


def render_connection_profiles(project_id: str) -> None:
    with st.expander(t("Conexiones del proyecto")):
        st.caption(
            t("Cada perfil queda aislado en data/connections/<proyecto>. La password no se guarda en el JSON del proyecto.")
        )
        profiles = service.list_connection_profiles(project_id)
        if profiles:
            st.dataframe(
                localize_rows([{"Perfil": item["profile_id"], "Adapter": item["adapter"]} for item in profiles]),
                hide_index=True,
                width="stretch",
            )
        with st.form(f"mariadb-profile-{project_id}"):
            profile_id = st.text_input(t("Nombre del perfil"), value="default", key='ui-streamlit_app-render_connection_profiles-256')
            host = st.text_input("Host", key='ui-streamlit_app-render_connection_profiles-257')
            port = st.number_input(t("Puerto"), min_value=1, max_value=65_535, value=3306, key='ui-streamlit_app-render_connection_profiles-258')
            user = st.text_input(t("Usuario"), key='ui-streamlit_app-render_connection_profiles-259')
            password = st.text_input("Password", type="password", key='ui-streamlit_app-render_connection_profiles-260')
            database = st.text_input(t("Base de datos"), key='ui-streamlit_app-render_connection_profiles-261')
            save_submitted = st.form_submit_button(t("Guardar perfil MariaDB"), key='ui-streamlit_app-render_connection_profiles-262')
            check_submitted = st.form_submit_button(t("Comprobar conexion"), key='ui-streamlit_app-render_connection_profiles-263')
            if save_submitted:
                try:
                    service.save_mariadb_connection_profile(
                        project_id,
                        profile_id,
                        host,
                        int(port),
                        user,
                        password,
                        database,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(t("Perfil '{v0}' guardado para este proyecto", v0=profile_id))
                    st.rerun()
            if check_submitted:
                try:
                    result = service.check_mariadb_connection(project_id, profile_id)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        t('Conexion read-only OK: {v0} / {v1}', v0=result['server'], v1=result['database'])
                    )


def render_project_admin(project_id: str, project) -> None:
    st.title(t("Proyecto"))
    st.caption(t('Administración del contexto seleccionado: {v0}', v0=project.name))
    if st.button(t("Volver a productos"), type="primary", key='ui-streamlit_app-render_project_admin-294'):
        st.session_state["active_product_area"] = "Atlas"
        st.rerun()
    render_project_overview(project_id, project)
    render_project_editor(project)
    render_bim_import(project_id, project)
    render_metadata_editor(project_id, project.metadata)
    render_connection_profiles(project_id)
    left_column, right_column = st.columns((3, 2))
    with left_column:
        render_concepts(project_id, project)
    with right_column:
        render_relations(project_id, project)
    export_column, snapshot_column = st.columns((2, 2))
    with export_column:
        render_export_actions(project_id)
    with snapshot_column:
        render_snapshots(project_id)


def render_project_editor(project) -> None:
    with st.expander(t("Editar proyecto")):
        with st.form("project-form"):
            project_name = st.text_input(t("Nombre del proyecto"), value=project.name, key='ui-streamlit_app-render_project_editor-317')
            project_description = st.text_area(t("Descripcion del proyecto"), value=project.description, key='ui-streamlit_app-render_project_editor-318')
            submitted = st.form_submit_button(t("Guardar datos del proyecto"), key='ui-streamlit_app-render_project_editor-319')
            if submitted:
                try:
                    service.update_project(project.id, project_name, project_description)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(t("Proyecto actualizado"))
                    st.rerun()


def render_bim_import(project_id: str, project) -> None:
    with st.expander(t("Importar modelo semantico"), expanded=not project.concepts and not project.relations):
        st.caption(
            t("Carga un model.bim, un archivo TMDL o un paquete PBIP .zip para poblar tablas, columnas, medidas y relaciones. "
            "El archivo original queda guardado localmente con hash para Atlas.")
        )
        uploaded_file = st.file_uploader(
            t("Archivo de modelo semantico"),
            type=["bim", "json", "tmdl", "zip", "pbip"],
            key=f"bim-uploader-{project_id}",
        )
        clear_existing = st.checkbox(
            t("Limpiar conceptos y relaciones actuales antes de importar"),
            value=not project.concepts and not project.relations,
            key=f"bim-clear-{project_id}",
        )
        snapshot_note = st.text_input(
            t("Nota para snapshot previo"),
            value="before-bim-import",
            key=f"bim-note-{project_id}",
        )
        if uploaded_file is not None and st.button(t("Importar modelo semantico"), key=f"bim-import-button-{project_id}"):
            try:
                _, summary = service.import_semantic_model_file(
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
                    t('Importacion BIM lista: {v0} tablas, {v1} columnas, {v2} medidas y {v3} relaciones detectadas.', v0=summary['tables'], v1=summary['columns'], v2=summary['measures'], v3=summary['relationships'])
                )
                st.rerun()


def render_concepts(project_id: str, project) -> None:
    st.subheader(t("Conceptos"))
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
        st.dataframe(localize_rows(rows), width="stretch", hide_index=True)
    else:
        st.info(t("Todavia no hay conceptos cargados."))

    with st.form("add-concept", clear_on_submit=True):
        st.markdown(t("### Agregar concepto"))
        name = st.text_input(t("Nombre del concepto"), key='ui-streamlit_app-render_concepts-390')
        definition = st.text_area(t("Definicion"), key='ui-streamlit_app-render_concepts-391')
        status = st.selectbox(t("Estado"), options=["draft", "review", "approved"], key='ui-streamlit_app-render_concepts-392', format_func=option_labels(["draft", "review", "approved"], t))
        tags = st.text_input(t("Tags separados por coma"), key='ui-streamlit_app-render_concepts-393')
        submitted = st.form_submit_button(t("Guardar concepto"), key='ui-streamlit_app-render_concepts-394')
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
                st.success(t("Concepto guardado"))
                st.rerun()

    if project.concepts:
        with st.expander(t("Editar o borrar concepto")):
            concept_options = {concept.id: concept for concept in project.concepts}
            selected_concept_id = st.selectbox(
                t("Concepto"),
                options=list(concept_options.keys()),
                format_func=option_labels(list(concept_options.keys()), lambda item: concept_options[item].name),
            key='ui-streamlit_app-render_concepts-413')
            selected_concept = concept_options[selected_concept_id]
            with st.form("edit-concept"):
                name = st.text_input(t("Nombre"), value=selected_concept.name, key='ui-streamlit_app-render_concepts-420')
                definition = st.text_area(t("Definicion"), value=selected_concept.definition, key='ui-streamlit_app-render_concepts-421')
                status = st.selectbox(
                    t("Estado"),
                    options=["draft", "review", "approved"],
                    index=["draft", "review", "approved"].index(selected_concept.status)
                    if selected_concept.status in ["draft", "review", "approved"]
                    else 0,
                key='ui-streamlit_app-render_concepts-422', format_func=option_labels(["draft", "review", "approved"], t))
                tags = st.text_input(t("Tags separados por coma"), value=", ".join(selected_concept.tags), key='ui-streamlit_app-render_concepts-429')
                save_submitted = st.form_submit_button(t("Guardar cambios"), key='ui-streamlit_app-render_concepts-430')
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
                        st.success(t("Concepto actualizado"))
                        st.rerun()
            if st.button(t("Borrar concepto"), type="secondary", key='ui-streamlit_app-render_concepts-446'):
                service.delete_concept(project_id, selected_concept_id)
                st.success(t("Concepto eliminado"))
                st.rerun()


def render_relations(project_id: str, project) -> None:
    st.subheader(t("Relaciones"))
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
        st.dataframe(localize_rows(rows), width="stretch", hide_index=True)
    else:
        st.info(t("Todavia no hay relaciones cargadas."))

    if len(project.concepts) < 2:
        st.caption(t("Necesitas al menos dos conceptos para definir relaciones."))
        return

    concept_options = {concept.id: concept.name for concept in project.concepts}
    with st.form("add-relation", clear_on_submit=True):
        st.markdown(t("### Agregar relacion"))
        source_id = st.selectbox(
            t("Origen"),
            options=list(concept_options.keys()),
            format_func=option_labels(list(concept_options.keys()), lambda item: concept_options[item]),
            key="source_id",
        )
        target_id = st.selectbox(
            t("Destino"),
            options=list(concept_options.keys()),
            format_func=option_labels(list(concept_options.keys()), lambda item: concept_options[item]),
            key="target_id",
        )
        relation_type = st.text_input(t("Tipo de relacion"), value="depends-on", key='ui-streamlit_app-render_relations-488')
        description = st.text_area(t("Descripcion"), key='ui-streamlit_app-render_relations-489')
        submitted = st.form_submit_button(t("Guardar relacion"), key='ui-streamlit_app-render_relations-490')
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
                st.success(t("Relacion guardada"))
                st.rerun()

    if project.relations:
        with st.expander(t("Editar o borrar relacion")):
            relation_options = {relation.id: relation for relation in project.relations}
            selected_relation_id = st.selectbox(
                t("Relacion"),
                options=list(relation_options.keys()),
                format_func=option_labels(list(relation_options.keys()), lambda item: t('{v0} --{v1}--> {v2}', v0=relation_options[item].source_id, v1=relation_options[item].relation_type, v2=relation_options[item].target_id)),
            key='ui-streamlit_app-render_relations-509')
            selected_relation = relation_options[selected_relation_id]
            with st.form("edit-relation"):
                source_id = st.selectbox(
                    t("Origen"),
                    options=list(concept_options.keys()),
                    index=list(concept_options.keys()).index(selected_relation.source_id),
                    format_func=option_labels(list(concept_options.keys()), lambda item: concept_options[item]),
                    key="edit_source_id",
                )
                target_id = st.selectbox(
                    t("Destino"),
                    options=list(concept_options.keys()),
                    index=list(concept_options.keys()).index(selected_relation.target_id),
                    format_func=option_labels(list(concept_options.keys()), lambda item: concept_options[item]),
                    key="edit_target_id",
                )
                relation_type = st.text_input(t("Tipo de relacion"), value=selected_relation.relation_type, key='ui-streamlit_app-render_relations-530')
                description = st.text_area(t("Descripcion"), value=selected_relation.description, key='ui-streamlit_app-render_relations-531')
                save_submitted = st.form_submit_button(t("Guardar cambios de relacion"), key='ui-streamlit_app-render_relations-532')
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
                        st.success(t("Relacion actualizada"))
                        st.rerun()
            if st.button(t("Borrar relacion"), type="secondary", key='ui-streamlit_app-render_relations-548'):
                service.delete_relation(project_id, selected_relation_id)
                st.success(t("Relacion eliminada"))
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="DataIA Ontology Workbench", layout="wide")
    render_language_selector()

    selected_id = render_project_selector()
    render_create_project()
    if not selected_id:
        st.info(t("Crea un proyecto desde la barra lateral para empezar."))
        return

    project = service.get_project(selected_id)
    st.session_state["selected_project_id"] = project.id
    context_gate = st.empty()
    project_navigation = st.sidebar.empty()
    context_is_ready = (
        st.session_state.get("project_context_ready")
        and st.session_state.get("project_context_project_id") == project.id
    )
    if not context_is_ready:
        project_navigation.empty()
        with context_gate.container():
            render_project_context_gate(project)
        return
    context_gate.empty()

    active_area = st.session_state.get("active_product_area", "Atlas")
    product_labels = dict(PRODUCT_STAGE_LABELS)
    with project_navigation.container():
        st.divider()
        st.subheader(project.name)
        st.caption(t("Ruta de trabajo"))
        if active_area == "Proyecto":
            if st.button(t("Volver a productos"), width="stretch", key='ui-streamlit_app-main-586'):
                st.session_state["active_product_area"] = "Atlas"
                st.rerun()
            selected_area = "Proyecto"
        else:
            if st.button(t("Administrar proyecto"), width="stretch", key='ui-streamlit_app-main-591'):
                st.session_state["active_product_area"] = "Proyecto"
                st.rerun()
            selected_area = st.radio(
                t("Producto"),
                options=list(PRODUCT_AREAS.keys()),
                index=list(PRODUCT_AREAS.keys()).index(active_area) if active_area in PRODUCT_AREAS else 0,
                format_func=option_labels(list(PRODUCT_AREAS.keys()), product_labels.get),
                key="product-navigation",
            )
    render_reviewer_identity()
    st.session_state["active_product_area"] = selected_area
    if selected_area == "Proyecto":
        render_project_admin(project.id, project)
        return

    if selected_area == "Atlas":
        render_atlas(service, project.id)
    elif selected_area == "Nexo":
        render_nexo(service, project.id)
    elif selected_area == "Argos":
        render_argos(service, project.id)


if __name__ == "__main__":
    main()
