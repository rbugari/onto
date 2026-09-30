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


store = ProjectStore(DATA_DIR / "projects")
service = WorkbenchService(store)


PRODUCT_AREAS = {
    "Atlas": "Atlas",
    "Nexo": "Nexo",
    "Argos": "Argos",
}

PRODUCT_STAGE_LABELS = {
    "Atlas": "1. Atlas · Diagnóstico",
    "Nexo": "2. Nexo · Validar conocimiento",
    "Argos": "3. Argos · Investigar el negocio",
}


def render_project_selector() -> str | None:
    projects = service.list_projects()
    if not projects:
        st.sidebar.info("No hay proyectos todavia. Crea uno para empezar.")
        return None

    labels = {project.id: project.name for project in projects}
    current_id = st.session_state.get("selected_project_id")
    selected_index = list(labels.keys()).index(current_id) if current_id in labels else 0
    selected_id = st.sidebar.selectbox(
        "Proyecto",
        options=list(labels.keys()),
        index=selected_index,
        format_func=lambda item: labels[item],
        key="project-selector",
    )
    if selected_id != current_id:
        st.session_state["selected_project_id"] = selected_id
        st.session_state["project_context_ready"] = False
        st.session_state["project_context_project_id"] = None
        st.session_state["active_product_area"] = "Atlas"
    return selected_id


def render_create_project() -> None:
    with st.sidebar.expander("Crear proyecto"):
        with st.form("create-project", clear_on_submit=True):
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
                    st.session_state["project_context_ready"] = False
                    st.session_state["project_context_project_id"] = None
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
                st.session_state["project_context_ready"] = False
                st.session_state["project_context_project_id"] = None
                st.success("Proyecto importado")
                st.rerun()


def render_project_context_gate(project) -> bool:
    if (
        st.session_state.get("project_context_ready")
        and st.session_state.get("project_context_project_id") == project.id
    ):
        return True

    st.title("Contexto de trabajo")
    st.header(project.name)
    st.caption(
        "Selecciona un proyecto para trabajar con sus datos, contexto y decisiones."
    )

    issues = service.validate_project(project.id)
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    infos = [issue for issue in issues if issue.level == "info"]

    if errors:
        st.error("El proyecto no puede abrirse todavía porque tiene errores estructurales.")
        for issue in errors:
            st.error(f"{issue.code}: {issue.message}")
    else:
        st.success("Proyecto validado. Listo para trabajar.")
        with st.expander("Ver validación del proyecto"):
            st.write(f"Conceptos: {len(project.concepts)}")
            st.write(f"Relaciones: {len(project.relations)}")
            st.write(f"Avisos: {len(warnings)}")
            for issue in warnings:
                st.warning(f"{issue.code}: {issue.message}")
            for issue in infos:
                st.info(f"{issue.code}: {issue.message}")

    open_project = st.button(
        "Abrir proyecto",
        type="primary",
        disabled=bool(errors),
        width="stretch",
    )
    if open_project and not errors:
        st.session_state["project_context_ready"] = True
        st.session_state["project_context_project_id"] = project.id
        st.session_state["active_product_area"] = "Atlas"
        st.rerun()
    return False


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


def render_connection_profiles(project_id: str) -> None:
    with st.expander("Conexiones del proyecto"):
        st.caption(
            "Cada perfil queda aislado en data/connections/<proyecto>. La password no se guarda en el JSON del proyecto."
        )
        profiles = service.list_connection_profiles(project_id)
        if profiles:
            st.dataframe(
                [{"Perfil": item["profile_id"], "Adapter": item["adapter"]} for item in profiles],
                hide_index=True,
                width="stretch",
            )
        with st.form(f"mariadb-profile-{project_id}"):
            profile_id = st.text_input("Nombre del perfil", value="default")
            host = st.text_input("Host")
            port = st.number_input("Puerto", min_value=1, max_value=65_535, value=3306)
            user = st.text_input("Usuario")
            password = st.text_input("Password", type="password")
            database = st.text_input("Base de datos")
            save_submitted = st.form_submit_button("Guardar perfil MariaDB")
            check_submitted = st.form_submit_button("Comprobar conexion")
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
                    st.success(f"Perfil '{profile_id}' guardado para este proyecto")
                    st.rerun()
            if check_submitted:
                try:
                    result = service.check_mariadb_connection(project_id, profile_id)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Conexion read-only OK: {result['server']} / {result['database']}"
                    )


def render_project_admin(project_id: str, project) -> None:
    st.title("Proyecto")
    st.caption(f"Administración del contexto seleccionado: {project.name}")
    if st.button("Volver a productos", type="primary"):
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
    with st.expander("Importar modelo semantico", expanded=not project.concepts and not project.relations):
        st.caption(
            "Carga un model.bim, un archivo TMDL o un paquete PBIP .zip para poblar tablas, columnas, medidas y relaciones. "
            "El archivo original queda guardado localmente con hash para Atlas."
        )
        uploaded_file = st.file_uploader(
            "Archivo de modelo semantico",
            type=["bim", "json", "tmdl", "zip", "pbip"],
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
        if uploaded_file is not None and st.button("Importar modelo semantico", key=f"bim-import-button-{project_id}"):
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
                    "Importacion BIM lista: "
                    f"{summary['tables']} tablas, {summary['columns']} columnas, "
                    f"{summary['measures']} medidas y {summary['relationships']} relaciones detectadas."
                )
                st.rerun()


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

    selected_id = render_project_selector()
    render_create_project()
    if not selected_id:
        st.info("Crea un proyecto desde la barra lateral para empezar.")
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
    with project_navigation.container():
        st.divider()
        st.subheader(project.name)
        st.caption("Ruta de trabajo")
        if active_area == "Proyecto":
            if st.button("Volver a productos", width="stretch"):
                st.session_state["active_product_area"] = "Atlas"
                st.rerun()
            selected_area = "Proyecto"
        else:
            if st.button("Administrar proyecto", width="stretch"):
                st.session_state["active_product_area"] = "Proyecto"
                st.rerun()
            selected_area = st.radio(
                "Producto",
                options=list(PRODUCT_AREAS.keys()),
                index=list(PRODUCT_AREAS.keys()).index(active_area) if active_area in PRODUCT_AREAS else 0,
                format_func=lambda item: PRODUCT_STAGE_LABELS[item],
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
