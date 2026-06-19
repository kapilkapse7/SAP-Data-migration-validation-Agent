"""Functional Consultant view — ad-hoc validation workspace (unchanged workflow)."""

import streamlit as st

from config import SAMPLE_FS_PATH, SAMPLE_PRELOAD_PATH, has_api_key
from graph import run_fc_pipeline
from services import audit_service, validation_service
from ui.common import read_uploaded_fs, read_uploaded_preload, render_validation_result

import pandas as pd


def render_fc_workspace(user) -> None:
    st.header("Functional Consultant — Validation Workspace")
    st.caption("Ad-hoc validation. Upload your own MDM FS and preload file — no pre-configured objects required.")

    if has_api_key():
        st.success("Gemini API key detected — AI rule extraction and email generation enabled.")
    else:
        st.warning("No Gemini API key found. Fallback parsers will be used where possible.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Upload MDM Functional Specification")
        fs_file = st.file_uploader(
            "MDM Functional Specification",
            type=["txt", "md", "csv", "xlsx", "xls", "pdf"],
            key="fc_fs_upload",
        )
    with col2:
        st.subheader("2. Upload Preload Excel")
        preload_file = st.file_uploader(
            "Preload Excel File", type=["xlsx", "xls"], key="fc_preload_upload"
        )

    with st.expander("Use sample data (for testing)"):
        c1, c2 = st.columns(2)
        use_sample_fs = c1.checkbox("Load sample MDM FS")
        use_sample_preload = c2.checkbox("Load sample preload Excel")

    fs_content = ""
    preload_df = None
    try:
        if use_sample_fs and SAMPLE_FS_PATH.exists():
            fs_content = SAMPLE_FS_PATH.read_text(encoding="utf-8")
        elif fs_file:
            fs_content, _ = read_uploaded_fs(fs_file)

        if use_sample_preload and SAMPLE_PRELOAD_PATH.exists():
            preload_df = pd.read_excel(SAMPLE_PRELOAD_PATH, engine="openpyxl")
        elif preload_file:
            preload_df = read_uploaded_preload(preload_file)
    except Exception as exc:
        st.error(f"Could not read input: {exc}")
        return

    if preload_df is not None:
        with st.expander("Preview Preload Data"):
            st.dataframe(preload_df, use_container_width=True)

    st.divider()
    if st.button("Run Validation", type="primary", use_container_width=True):
        if not fs_content.strip():
            st.error("Please upload or load an MDM Functional Specification.")
            return
        if preload_df is None or preload_df.empty:
            st.error("Please upload or load a preload Excel file.")
            return
        with st.spinner("Running multi-agent validation pipeline..."):
            result = run_fc_pipeline(fs_content, preload_df)
        st.session_state["validation_result"] = result
        # FC runs are ad-hoc (no object), but still recorded for audit/history
        validation_service.record_run(
            object_id=None,
            user_id=user.id,
            total_records=result.get("total_records", 0),
            passed_records=result.get("passed_records", 0),
            failed_records=result.get("failed_records", 0),
            validation_results=result.get("validation_results", []),
        )
        audit_service.log_action(user, "RUN_VALIDATION", "ad-hoc (FC workspace)")

    render_validation_result(st.session_state.get("validation_result"))
