"""Widgets shared by Atlas, Nexo and Argos."""
from __future__ import annotations

import streamlit as st

from onto_ui.i18n import LocalizedLabels, localize_rows, localized_tabs, t

REVIEWER_KEY = "reviewer-name"
REVIEWER_ROLE_KEY = "reviewer-role"


def render_reviewer_identity() -> None:
    """Sidebar identity reused by every review decision in the session."""
    with st.sidebar.expander(t("Revisor/a de esta sesión"), expanded=not st.session_state.get(REVIEWER_KEY)):
        st.text_input(t("Nombre"), key=REVIEWER_KEY, placeholder="Ana Pérez")
        st.text_input(t("Rol"), key=REVIEWER_ROLE_KEY, placeholder=t("Responsable de negocio"))


def reviewer() -> tuple[str, str]:
    return (
        str(st.session_state.get(REVIEWER_KEY, "")).strip(),
        str(st.session_state.get(REVIEWER_ROLE_KEY, "")).strip(),
    )


def require_reviewer() -> bool:
    name, _ = reviewer()
    if not name:
        st.warning(t("Indicá tu nombre en **Revisor/a de esta sesión** (barra lateral) para registrar decisiones."))
    return bool(name)


def render_discovery_proposal(proposal: dict, key: str) -> None:
    cores = proposal.get("business_cores", [])
    if cores:
        st.subheader(t("Nucleos del negocio"))
        for core in cores:
            st.markdown("**" + core["name"] + "**")
            st.write(core["definition"])
            st.caption(" · ".join(core["entities"]))
        st.subheader(t("Entidades principales"))
    for entity in proposal["entities"]:
        if cores:
            if entity.get("importance") == "supporting":
                continue
            with st.expander(entity["name"]):
                st.write(entity["definition"])
                st.caption(entity["reason"])
                for prop in entity.get("properties", []):
                    st.write(f"{prop['name']}: {prop['definition']}")
        else:
            st.markdown("**" + entity["name"] + "**")
            st.write(entity["definition"])
            for prop in entity.get("properties", []):
                st.write(f"{prop['name']}: {prop['definition']}")
    supporting = [entity for entity in proposal["entities"] if entity.get("importance") == "supporting"]
    if supporting:
        with st.expander(t("Entidades secundarias ({count})", count=len(supporting))):
            for entity in supporting:
                st.markdown("**" + entity["name"] + "**")
                st.write(entity["definition"])
                st.caption(entity["reason"])
                for prop in entity.get("properties", []):
                    st.write(f"{prop['name']}: {prop['definition']}")
    if proposal.get("rules"):
        st.subheader(t("Reglas y calculos propuestos"))
        st.dataframe(localize_rows([{"Nombre": rule["name"], "Definicion": rule["definition"],
            "Validacion pendiente": rule["validation_needed"], "Entidades": ", ".join(rule["entities"])}
            for rule in proposal["rules"]]), hide_index=True, width="stretch")
    if proposal["relationships"]:
        with st.expander(t("Relaciones propuestas")):
            st.dataframe(localize_rows([{"Origen": relation["source"], "Relacion": relation["name"],
                "Destino": relation["target"], "Definicion": relation["definition"]}
                for relation in proposal["relationships"]]), hide_index=True, width="stretch")
    if cores:
        tabs = localized_tabs(["Preguntas de negocio", "Dudas tecnicas", "Preguntas para analizar"],
                              key=f"discovery-questions-{key}")
        readiness = {"data_required": "Requiere datos actuales", "validation_required": "Requiere validacion y datos",
                     "unsupported": "No soportada con los insumos actuales"}
        for tab, group in zip(tabs, ("business_questions", "technical_questions", "analytical_questions")):
            with tab:
                if not proposal.get(group):
                    st.caption(t("Sin preguntas propuestas"))
                for question in proposal.get(group, []):
                    st.markdown("**" + question["question"] + "**")
                    st.write(question.get("why", question.get("value", "")))
                    st.caption(" · ".join(question["entities"]))
                    if group == "analytical_questions":
                        st.caption(t(readiness[question["readiness"]]))
                        st.write(t("Falta: {items}", items="; ".join(question["missing"])))
                    else:
                        st.caption(t("Alta" if question["priority"] == "high" else "Media"))
    elif proposal.get("questions"):
        st.subheader(t("Preguntas prioritarias"))
        for question in proposal["questions"]:
            st.write(question)
