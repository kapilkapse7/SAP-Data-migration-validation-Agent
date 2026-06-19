"""
SAP Data Migration Governance Platform — Streamlit entry point.

Role-Based Access Control over the existing multi-agent (LangGraph) validation
pipeline. Routes the logged-in user to the Admin, Functional Consultant, or
Business Analyst experience.
"""

import logging
import sys
from pathlib import Path

import streamlit as st

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import ROLE_ADMIN, ROLE_BA, ROLE_FC  # noqa: E402
from database.session import init_db  # noqa: E402
from ui.login import is_authenticated, render_login  # noqa: E402
from ui.sidebar import render_sidebar  # noqa: E402
from ui import admin_view, ba_view, fc_view  # noqa: E402
from ui.dashboards import render_admin_dashboard  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "migration_agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def _route_admin(page: str, user) -> None:
    if page == "Dashboard":
        render_admin_dashboard()
    elif page == "Manage Streams":
        admin_view.render_manage_streams(user)
    elif page == "Manage Objects":
        admin_view.render_manage_objects(user)
    elif page == "Upload / Edit FS":
        admin_view.render_upload_fs(user)
    elif page == "Audit Trail":
        admin_view.render_audit_trail(user)


def _route_ba(page: str, user) -> None:
    if page == "Global Dashboard":
        ba_view.render_ba_dashboard(user)
    elif page == "Run Validation":
        ba_view.render_ba_validation(user)


def main() -> None:
    init_db()

    if not is_authenticated():
        render_login()
        return

    st.set_page_config(
        page_title="SAP Migration Governance Platform",
        page_icon="📋",
        layout="wide",
    )

    user = st.session_state["user"]
    page = render_sidebar(user)

    st.title("SAP Data Migration Governance Platform")

    if user.role == ROLE_ADMIN:
        _route_admin(page, user)
    elif user.role == ROLE_FC:
        fc_view.render_fc_workspace(user)
    elif user.role == ROLE_BA:
        _route_ba(page, user)
    else:
        st.error(f"Unknown role: {user.role}")


if __name__ == "__main__":
    main()
