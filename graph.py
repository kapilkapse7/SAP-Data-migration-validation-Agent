"""Role-aware LangGraph workflow for the SAP Data Migration Governance Platform.

Three flows share one compiled graph, selected by `state["mode"]`:

    Admin:  START -> rule_extraction -> store_rules -> END
    FC:     START -> rule_extraction -> validation -> report -> email -> END
    BA:     START -> load_stored_rules -> validation -> report -> email -> END
"""

import logging

from langgraph.graph import END, START, StateGraph

from agents.email_generator import generate_email_draft
from agents.report_generator import generate_validation_report
from agents.rule_extractor import extract_validation_rules
from agents.rule_loader import load_stored_rules
from agents.rule_store import store_rules
from agents.validator import validate_preload_data
from state import MigrationState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------
def _route_entry(state: MigrationState) -> str:
    """Choose the entry node based on the logged-in user's role/mode."""
    mode = state.get("mode", "fc")
    if mode == "ba":
        return "load_rules"
    return "extract"  # admin + fc both start with rule extraction


def _route_after_extraction(state: MigrationState) -> str:
    """After rule extraction: Admin stores rules; FC continues to validation."""
    if state.get("error") and not state.get("rules"):
        logger.warning("Stopping pipeline after rule extraction failure")
        return "end"
    if state.get("mode") == "admin":
        return "store"
    return "validate"


def _route_after_loading(state: MigrationState) -> str:
    """After loading stored rules (BA): validate or stop if no rules."""
    if state.get("error") and not state.get("rules"):
        return "end"
    return "validate"


def _route_after_validation(state: MigrationState) -> str:
    """Route to report generation or end early if validation could not run."""
    if state.get("error") and not state.get("validation_results"):
        logger.warning("Stopping pipeline after validation failure")
        return "end"
    return "report"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
def build_governance_graph():
    """Build and compile the role-aware multi-agent workflow."""
    workflow = StateGraph(MigrationState)

    workflow.add_node("rule_extraction", extract_validation_rules)
    workflow.add_node("load_stored_rules", load_stored_rules)
    workflow.add_node("store_rules", store_rules)
    workflow.add_node("validation", validate_preload_data)
    workflow.add_node("report_generation", generate_validation_report)
    workflow.add_node("email_generation", generate_email_draft)

    workflow.add_conditional_edges(
        START,
        _route_entry,
        {"extract": "rule_extraction", "load_rules": "load_stored_rules"},
    )
    workflow.add_conditional_edges(
        "rule_extraction",
        _route_after_extraction,
        {"store": "store_rules", "validate": "validation", "end": END},
    )
    workflow.add_edge("store_rules", END)
    workflow.add_conditional_edges(
        "load_stored_rules",
        _route_after_loading,
        {"validate": "validation", "end": END},
    )
    workflow.add_conditional_edges(
        "validation",
        _route_after_validation,
        {"report": "report_generation", "end": END},
    )
    workflow.add_edge("report_generation", "email_generation")
    workflow.add_edge("email_generation", END)

    return workflow.compile()


# Compile once at import time
_GRAPH = build_governance_graph()


def _base_state() -> MigrationState:
    return {
        "fs_content": "",
        "rules": {},
        "preload_df": None,
        "validation_results": [],
        "report_path": "",
        "email_draft": "",
        "error": "",
        "total_records": 0,
        "passed_records": 0,
        "failed_records": 0,
    }


# ---------------------------------------------------------------------------
# Public entry points (one per role)
# ---------------------------------------------------------------------------
def run_admin_pipeline(
    fs_content: str,
    object_id: int,
    fs_file_name: str,
    fs_bytes: bytes | None = None,
) -> MigrationState:
    """Admin: extract rules from an uploaded FS and store them as a new version."""
    state = {
        **_base_state(),
        "mode": "admin",
        "fs_content": fs_content,
        "object_id": object_id,
        "fs_file_name": fs_file_name,
        "fs_bytes": fs_bytes,
    }
    logger.info("Running ADMIN pipeline for object %s", object_id)
    return _GRAPH.invoke(state)


def run_fc_pipeline(fs_content: str, preload_df) -> MigrationState:
    """Functional Consultant: ad-hoc extract -> validate -> report -> email."""
    state = {
        **_base_state(),
        "mode": "fc",
        "fs_content": fs_content,
        "preload_df": preload_df,
    }
    logger.info("Running FC pipeline")
    return _GRAPH.invoke(state)


def run_ba_pipeline(object_id: int, preload_df, user_id: int | None = None) -> MigrationState:
    """Business Analyst: load stored rules -> validate -> report -> email."""
    state = {
        **_base_state(),
        "mode": "ba",
        "object_id": object_id,
        "user_id": user_id,
        "preload_df": preload_df,
    }
    logger.info("Running BA pipeline for object %s", object_id)
    return _GRAPH.invoke(state)


# Backwards-compatible alias for the original FC flow
def run_validation_pipeline(fs_content: str, preload_df) -> MigrationState:
    """Legacy entry point — equivalent to the Functional Consultant pipeline."""
    return run_fc_pipeline(fs_content, preload_df)
