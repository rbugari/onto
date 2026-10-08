"""Widgets shared by Atlas, Nexo and Argos."""
from __future__ import annotations

import streamlit as st

from onto_ui.i18n import LocalizedLabels, localize_rows, t

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
