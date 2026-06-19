"""Login screen and session-state authentication helpers."""

import streamlit as st

from auth.auth_service import authenticate
from services.audit_service import log_action


def is_authenticated() -> bool:
    return st.session_state.get("user") is not None


def current_user():
    return st.session_state.get("user")


def logout() -> None:
    user = st.session_state.get("user")
    if user:
        log_action(user, "LOGOUT")
    for key in ("user", "validation_result", "selected_stream_id", "selected_object_id"):
        st.session_state.pop(key, None)
    st.rerun()


def render_login() -> None:
    """Render the login form."""
    st.set_page_config(page_title="SAP Migration Governance — Login", page_icon="🔐")
    st.title("SAP Data Migration Governance Platform")
    st.caption("Role-Based Access Control — please sign in")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        user = authenticate(username.strip(), password)
        if user:
            st.session_state["user"] = user
            log_action(user, "LOGIN")
            st.rerun()
        else:
            st.error("Invalid username or password.")

    with st.expander("Default demo credentials"):
        st.markdown(
            "- **Admin** — `admin` / `admin123`\n"
            "- **Functional Consultant** — `consultant` / `fc123`\n"
            "- **Business Analyst** — `analyst` / `ba123`"
        )
