"""Sidebar showing the logged-in user, role, navigation, and logout."""

import streamlit as st

from config import ROLE_ADMIN, ROLE_BA, ROLE_FC
from ui.login import logout

NAV_BY_ROLE = {
    ROLE_ADMIN: ["Dashboard", "Manage Streams", "Manage Objects", "Upload / Edit FS", "Audit Trail"],
    ROLE_FC: ["Validation Workspace"],
    ROLE_BA: ["Global Dashboard", "Run Validation"],
}


def render_sidebar(user) -> str:
    """Render sidebar; return the selected navigation page."""
    with st.sidebar:
        st.markdown("### SAP Migration Governance")
        st.markdown(f"**Logged in:** {user.username}")
        st.markdown(f"**Role:** {user.role}")
        st.divider()

        pages = NAV_BY_ROLE.get(user.role, [])
        page = st.radio("Navigation", pages, label_visibility="collapsed") if pages else ""

        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()

    return page
