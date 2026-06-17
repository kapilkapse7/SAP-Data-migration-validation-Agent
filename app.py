"""
SAP Data Migration Validation Agent — Streamlit Application.
Automates SAP Master Data Migration preload validation using business rules
extracted from an MDM Functional Specification document.
"""
import io
import json
import logging
import os
import sys
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
# Ensure project root is on the Python path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
from graph import run_validation_pipeline  # noqa: E402
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv(PROJECT_ROOT / ".env")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "migration_agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)
SAMPLE_FS_PATH = PROJECT_ROOT / "sample_data" / "mdm_fs.txt"
SAMPLE_PRELOAD_PATH = PROJECT_ROOT / "sample_data" / "preload.xlsx"
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def read_uploaded_fs(uploaded_file) -> str:
    """Read MDM Functional Specification content from an uploaded file."""
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()
    if name.endswith((".txt", ".md", ".csv")):
        return raw.decode("utf-8", errors="replace")
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(raw))
        return df.to_string(index=False)
    # Default: attempt UTF-8 text decode
    return raw.decode("utf-8", errors="replace")
def read_uploaded_preload(uploaded_file) -> pd.DataFrame | None:
    """Load preload Excel data from an uploaded file."""
    if uploaded_file is None:
        return None
    try:
        return pd.read_excel(io.BytesIO(uploaded_file.getvalue()), engine="openpyxl")
    except Exception as exc:
        logger.exception("Failed to read preload Excel: %s", exc)
        raise ValueError(f"Could not read preload Excel file: {exc}") from exc
def check_api_key() -> bool:
    """Return True if a Gemini API key is configured."""
    return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="SAP Data Migration Validation Agent",
        page_icon="📋",
        layout="wide",
    )
    st.title("SAP Data Migration Validation Agent")
    st.markdown(
        "Automate **SAP Master Data Migration** preload validation using business rules "
        "defined in your MDM Functional Specification document."
    )

    # API key status
    if check_api_key():
        st.success("Gemini API key detected — AI-powered rule extraction and email generation enabled.")
    else:
        st.warning(
            "No Gemini API key found. Set `GOOGLE_API_KEY` in `.env` for full AI features. "
            "Fallback parsers will be used where possible."
        )
    col_upload_fs, col_upload_preload = st.columns(2)

    with col_upload_fs:
        st.subheader("1. Upload MDM Functional Specification")
        fs_file = st.file_uploader(
            "MDM Functional Specification",
            type=["txt", "md", "csv", "xlsx", "xls"],
            help="Upload the MDM Functional Specification document containing field validation rules.",
            key="fs_upload",
        )

    with col_upload_preload:
        st.subheader("2. Upload Preload Excel")
        preload_file = st.file_uploader(
            "Preload Excel File",
            type=["xlsx", "xls"],
            help="Upload the SAP migration preload Excel file to validate.",
            key="preload_upload",
        )
    # Sample data shortcuts
    with st.expander("Use sample data (for testing)"):
        col_s1, col_s2 = st.columns(2)
        use_sample_fs = col_s1.checkbox("Load sample MDM FS", value=False)
        use_sample_preload = col_s2.checkbox("Load sample preload Excel", value=False)
    # Resolve inputs
    fs_content = ""
    preload_df: pd.DataFrame | None = None
    try:
        if use_sample_fs and SAMPLE_FS_PATH.exists():
            fs_content = SAMPLE_FS_PATH.read_text(encoding="utf-8")
            st.info(f"Loaded sample MDM FS from `{SAMPLE_FS_PATH.name}`")
        elif fs_file:
            fs_content = read_uploaded_fs(fs_file)
        if use_sample_preload and SAMPLE_PRELOAD_PATH.exists():
            preload_df = pd.read_excel(SAMPLE_PRELOAD_PATH, engine="openpyxl")
            st.info(f"Loaded sample preload from `{SAMPLE_PRELOAD_PATH.name}`")
        elif preload_file:
            preload_df = read_uploaded_preload(preload_file)
    except ValueError as exc:
        st.error(str(exc))
        return
    # Preview uploaded data
    if fs_content:
        with st.expander("Preview MDM Functional Specification"):
            st.text(fs_content[:3000] + ("..." if len(fs_content) > 3000 else ""))
    if preload_df is not None:
        with st.expander("Preview Preload Data"):
            st.dataframe(preload_df, use_container_width=True)
    st.divider()
    # Run validation
    run_clicked = st.button("Run Validation", type="primary", use_container_width=True)

    if run_clicked:
        if not fs_content.strip():
            st.error("Please upload or load an MDM Functional Specification document.")
            return
        if preload_df is None or preload_df.empty:
            st.error("Please upload or load a preload Excel file.")
            return
        with st.spinner("Running multi-agent validation pipeline..."):
            try:
                result = run_validation_pipeline(fs_content, preload_df)
                st.session_state["validation_result"] = result
            except Exception as exc:
                logger.exception("Pipeline execution failed: %s", exc)
                st.error(f"Validation pipeline failed: {exc}")
                return
    # Display results
    result = st.session_state.get("validation_result")
    if not result:
        return
    if result.get("error"):
        st.error(result["error"])

    # Extracted rules
    st.subheader("Extracted Validation Rules")
    rules = result.get("rules", {})
    if rules:
        st.json(rules)
    else:
        st.info("No rules were extracted.")
    # Validation summary
    st.subheader("Validation Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", result.get("total_records", 0))
    m2.metric("Passed Records", result.get("passed_records", 0))
    m3.metric("Failed Records", result.get("failed_records", 0))
    failed_checks = sum(
        1 for r in result.get("validation_results", []) if r.get("Status") == "FAIL"
    )
    m4.metric("Failed Checks", failed_checks)
    validation_results = result.get("validation_results", [])
    if validation_results:
        results_df = pd.DataFrame(validation_results)
        fail_df = results_df[results_df["Status"] == "FAIL"]
        with st.expander("View all validation results"):
            st.dataframe(results_df, use_container_width=True)
        if not fail_df.empty:
            st.subheader("Failed Validations")
            st.dataframe(fail_df, use_container_width=True)
    # Download report
    st.subheader("Validation Report")
    report_path = result.get("report_path", "")
    if report_path and Path(report_path).exists():
        with open(report_path, "rb") as f:
           st.download_button(
                label="Download Validation_Report.xlsx",
                data=f.read(),
                file_name="Validation_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    else:
        st.info("Report not available.")
    # Email draft
    st.subheader("Business Email Draft")
    email_draft = result.get("email_draft", "")
    if email_draft:
        st.text_area("Generated Email", value=email_draft, height=400)
        st.download_button(
            label="Download Email Draft",
            data=email_draft,
            file_name="validation_email_draft.txt",
            mime="text/plain",
            use_container_width=True,
        )
    else:
        st.info("Email draft not available.")
if __name__ == "__main__":
    main()