"""LangGraph workflow definition for the SAP Data Migration Validation pipeline."""

import logging

from langgraph.graph import END, START, StateGraph

from agents.email_generator import generate_email_draft
from agents.report_generator import generate_validation_report
from agents.rule_extractor import extract_validation_rules
from agents.validator import validate_preload_data
from state import MigrationState

logger = logging.getLogger(__name__)


def _should_continue_after_rules(state: MigrationState) -> str:
    """Route to validation or end early if rule extraction failed."""
    if state.get("error") and not state.get("rules"):
        logger.warning("Stopping pipeline after rule extraction failure")
        return "end"
    return "validate"


def _should_continue_after_validation(state: MigrationState) -> str:
    """Route to report generation or end early if validation could not run."""
    if state.get("error") and not state.get("validation_results"):
        logger.warning("Stopping pipeline after validation failure")
        return "end"
    return "report"


def build_validation_graph() -> StateGraph:
    """
    Build and compile the multi-agent LangGraph workflow.

    Workflow:
        START → Rule Extraction → Validation → Report Generation → Email Generation → END
    """
    workflow = StateGraph(MigrationState)

    workflow.add_node("rule_extraction", extract_validation_rules)
    workflow.add_node("validation", validate_preload_data)
    workflow.add_node("report_generation", generate_validation_report)
    workflow.add_node("email_generation", generate_email_draft)

    workflow.add_edge(START, "rule_extraction")
    workflow.add_conditional_edges(
        "rule_extraction",
        _should_continue_after_rules,
        {"validate": "validation", "end": END},
    )
    workflow.add_conditional_edges(
        "validation",
        _should_continue_after_validation,
        {"report": "report_generation", "end": END},
    )
    workflow.add_edge("report_generation", "email_generation")
    workflow.add_edge("email_generation", END)

    return workflow.compile()


def run_validation_pipeline(
    fs_content: str,
    preload_df,
) -> MigrationState:
    """
    Execute the full validation pipeline and return final state.

    Args:
        fs_content: Text content of the MDM Functional Specification document.
        preload_df: Pandas DataFrame loaded from the preload Excel file.

    Returns:
        Final MigrationState after all agents have run.
    """
    graph = build_validation_graph()

    initial_state: MigrationState = {
        "fs_content": fs_content,
        "rules": {},
        "preload_df": preload_df,
        "validation_results": [],
        "report_path": "",
        "email_draft": "",
        "error": "",
        "total_records": 0,
        "passed_records": 0,
        "failed_records": 0,
    }

    logger.info("Starting SAP Data Migration Validation pipeline")
    result = graph.invoke(initial_state)
    logger.info("Pipeline completed")
    return result
