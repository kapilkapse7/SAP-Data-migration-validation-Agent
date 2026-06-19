"""Shared UI helpers: file reading and validation-result rendering."""

import io
from pathlib import Path

import pandas as pd
import streamlit as st


def read_uploaded_fs(uploaded_file) -> tuple[str, bytes]:
    """Return (text_content, raw_bytes) from an uploaded FS file."""
    if uploaded_file is None:
        return "", b""
    raw = uploaded_file.getvalue()
    name = uploaded_file.name.lower()
    if name.endswith((".txt", ".md", ".csv")):
        return raw.decode("utf-8", errors="replace"), raw
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(raw))
        return df.to_string(index=False), raw
    return raw.decode("utf-8", errors="replace"), raw


def read_uploaded_preload(uploaded_file) -> pd.DataFrame | None:
    """Load a preload Excel file into a DataFrame."""
    if uploaded_file is None:
        return None
    return pd.read_excel(io.BytesIO(uploaded_file.getvalue()), engine="openpyxl")


def render_validation_result(result: dict) -> None:
    """Render rules, summary metrics, failures, report, and email for a run."""
    if not result:
        return
    if result.get("error"):
        st.error(result["error"])

    # Extracted / loaded rules
    st.subheader("Validation Rules")
    rules = result.get("rules", {})
    if rules:
        with st.expander(f"View {len(rules)} rules", expanded=False):
            st.json(rules)
    else:
        st.info("No rules available.")

    # Summary metrics
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
        with st.expander("View all validation results"):
            st.dataframe(results_df, use_container_width=True)
        fail_df = results_df[results_df["Status"] == "FAIL"]
        if not fail_df.empty:
            st.subheader("Failed Validations")
            st.dataframe(fail_df, use_container_width=True)

    # Report download
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
        st.text_area("Generated Email", value=email_draft, height=350)
        st.download_button(
            label="Download Email Draft",
            data=email_draft,
            file_name="validation_email_draft.txt",
            mime="text/plain",
            use_container_width=True,
        )
    else:
        st.info("Email draft not available.")
