"""Admin views — manage streams, objects, FS upload/versioning, and audit trail."""

import pandas as pd
import streamlit as st

from config import has_api_key
from graph import run_admin_pipeline
from services import audit_service, fs_service, stream_service
from ui.common import read_uploaded_fs
from ui.dashboards import render_admin_dashboard


def _stream_selectbox(label: str = "Stream"):
    streams = stream_service.list_streams()
    if not streams:
        st.info("No streams yet. Create one under 'Manage Streams'.")
        return None, streams
    options = {f"{s['stream_name']} (id {s['id']})": s["id"] for s in streams}
    choice = st.selectbox(label, list(options.keys()))
    return options[choice], streams


# ---------------------------------------------------------------------------
# Manage Streams
# ---------------------------------------------------------------------------
def render_manage_streams(user) -> None:
    st.header("Manage Streams")

    with st.form("create_stream"):
        st.subheader("Create Stream")
        name = st.text_input("Stream Name", placeholder="O2C, P2P, R2R, MDG")
        desc = st.text_input("Description (optional)")
        submitted = st.form_submit_button("Create Stream")
    if submitted:
        try:
            stream_service.create_stream(name, desc)
            audit_service.log_action(user, "CREATE_STREAM", name)
            st.success(f"Stream '{name}' created.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Existing Streams")
    streams = stream_service.list_streams()
    if streams:
        st.dataframe(pd.DataFrame(streams), use_container_width=True)
    else:
        st.info("No streams created yet.")


# ---------------------------------------------------------------------------
# Manage Objects
# ---------------------------------------------------------------------------
def render_manage_objects(user) -> None:
    st.header("Manage Migration Objects")
    stream_id, streams = _stream_selectbox("Select Stream")
    if stream_id is None:
        return

    with st.form("create_object"):
        st.subheader("Create Object")
        obj_name = st.text_input("Object Name", placeholder="Business Partner, CMIR, Vendor Master...")
        obj_desc = st.text_input("Description (optional)")
        submitted = st.form_submit_button("Create Object")
    if submitted:
        try:
            stream_service.create_object(stream_id, obj_name, obj_desc)
            audit_service.log_action(user, "CREATE_OBJECT", f"{obj_name} (stream {stream_id})")
            st.success(f"Object '{obj_name}' created.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Objects in Stream")
    objects = stream_service.list_objects(stream_id)
    if objects:
        st.dataframe(pd.DataFrame(objects), use_container_width=True)
    else:
        st.info("No objects in this stream yet.")


# ---------------------------------------------------------------------------
# Upload / Edit Functional Specification
# ---------------------------------------------------------------------------
def render_upload_fs(user) -> None:
    st.header("Upload / Edit MDM Functional Specification")
    if not has_api_key():
        st.warning("No Gemini API key configured — rule extraction will use the fallback parser.")

    stream_id, _ = _stream_selectbox("Select Stream")
    if stream_id is None:
        return

    objects = stream_service.list_objects(stream_id)
    if not objects:
        st.info("This stream has no objects. Create one under 'Manage Objects'.")
        return

    obj_options = {o["object_name"]: o["id"] for o in objects}
    obj_name = st.selectbox("Select Object", list(obj_options.keys()))
    object_id = obj_options[obj_name]

    # Version history
    versions = fs_service.list_fs_versions(object_id)
    if versions:
        st.markdown("**Version History**")
        st.dataframe(pd.DataFrame(versions), use_container_width=True)
    else:
        st.info("No Functional Specification uploaded for this object yet.")

    st.divider()
    st.subheader("Upload New Version")
    fs_file = st.file_uploader(
        "MDM Functional Specification",
        type=["txt", "md", "csv", "xlsx", "xls", "pdf"],
        key=f"admin_fs_{object_id}",
        help="Uploading creates a new version, regenerates rules, and stores them.",
    )

    if st.button("Extract Rules & Store Version", type="primary", use_container_width=True):
        if fs_file is None:
            st.error("Please upload a Functional Specification document.")
            return
        try:
            fs_content, fs_bytes = read_uploaded_fs(fs_file)
        except Exception as exc:
            st.error(f"Could not read document: {exc}")
            return
        if not fs_content.strip():
            st.error("The uploaded document appears to be empty.")
            return

        with st.spinner("Extracting and storing rules..."):
            result = run_admin_pipeline(
                fs_content=fs_content,
                object_id=object_id,
                fs_file_name=fs_file.name,
                fs_bytes=fs_bytes,
            )

        if result.get("error"):
            st.error(result["error"])
            return

        version = result.get("stored_version")
        rules = result.get("rules", {})
        audit_service.log_action(
            user, "UPLOAD_FS", f"{obj_name} v{version} ({len(rules)} rules)"
        )
        st.success(f"Stored version {version} with {len(rules)} extracted rules.")
        with st.expander("View extracted rules", expanded=True):
            st.json(rules)
        st.rerun()


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------
def render_audit_trail(user) -> None:
    st.header("Audit Trail")
    entries = audit_service.list_recent(300)
    if entries:
        st.dataframe(pd.DataFrame(entries), use_container_width=True)
    else:
        st.info("No audit entries recorded yet.")
