"""Business Analyst view — stream/object selection, validation, and dashboards."""

import streamlit as st

from graph import run_ba_pipeline
from services import audit_service, fs_service, stream_service, validation_service
from ui.common import read_uploaded_preload, render_validation_result
from ui.dashboards import (
    render_global_dashboard,
    render_object_dashboard,
    render_stream_dashboard,
)


def render_ba_dashboard(user) -> None:
    """Global + drill-down (stream / object) dashboards for the BA."""
    render_global_dashboard()
    st.divider()

    streams = stream_service.list_streams()
    if not streams:
        st.info("No streams configured by Admin yet.")
        return

    st.subheader("Drill Down")
    stream_options = {s["stream_name"]: s["id"] for s in streams}
    stream_name = st.selectbox("Select Stream to inspect", list(stream_options.keys()))
    stream_id = stream_options[stream_name]
    render_stream_dashboard(stream_id)

    objects = stream_service.list_objects(stream_id)
    if objects:
        st.divider()
        obj_options = {o["object_name"]: o["id"] for o in objects}
        obj_name = st.selectbox("Select Object to inspect", list(obj_options.keys()))
        render_object_dashboard(obj_options[obj_name])


def render_ba_validation(user) -> None:
    """The BA validation workflow against pre-configured objects."""
    st.header("Business Analyst — Run Validation")
    st.caption("Validate a preload file against Admin-approved rules. No FS upload required.")

    # Step 1: Select Stream
    streams = stream_service.list_streams()
    if not streams:
        st.info("No streams configured by Admin yet.")
        return
    stream_options = {s["stream_name"]: s["id"] for s in streams}
    stream_name = st.selectbox("Step 1 — Select Stream", list(stream_options.keys()))
    stream_id = stream_options[stream_name]

    # Step 2: Select Object
    objects = stream_service.list_objects(stream_id)
    if not objects:
        st.info("This stream has no objects yet. Ask an Admin to configure them.")
        return
    obj_options = {o["object_name"]: o["id"] for o in objects}
    obj_name = st.selectbox("Step 2 — Select Object", list(obj_options.keys()))
    object_id = obj_options[obj_name]

    # Step 3: Auto-load latest approved rules (no upload shown to BA)
    rules = fs_service.get_latest_rules(object_id)
    if not rules:
        st.error(
            f"No approved MDM FS rules are configured for '{obj_name}'. "
            "Please ask an Admin to upload a Functional Specification."
        )
        return
    st.success(f"Step 3 — Loaded {len(rules)} approved rules for '{obj_name}'.")
    with st.expander("View loaded rules"):
        st.json(rules)

    # Step 4: Upload preload
    st.subheader("Step 4 — Upload Preload Excel")
    preload_file = st.file_uploader("Preload Excel File", type=["xlsx", "xls"], key=f"ba_preload_{object_id}")

    # Step 5: Run validation
    st.divider()
    if st.button("Step 5 — Run Validation", type="primary", use_container_width=True):
        if preload_file is None:
            st.error("Please upload a preload Excel file.")
            return
        try:
            preload_df = read_uploaded_preload(preload_file)
        except Exception as exc:
            st.error(f"Could not read preload file: {exc}")
            return
        if preload_df is None or preload_df.empty:
            st.error("The preload file appears to be empty.")
            return

        with st.spinner("Running validation against stored rules..."):
            result = run_ba_pipeline(object_id, preload_df, user_id=user.id)
        st.session_state["validation_result"] = result

        validation_service.record_run(
            object_id=object_id,
            user_id=user.id,
            total_records=result.get("total_records", 0),
            passed_records=result.get("passed_records", 0),
            failed_records=result.get("failed_records", 0),
            validation_results=result.get("validation_results", []),
        )
        audit_service.log_action(user, "RUN_VALIDATION", f"{obj_name} (stream {stream_name})")

    # Step 6: Results
    render_validation_result(st.session_state.get("validation_result"))
