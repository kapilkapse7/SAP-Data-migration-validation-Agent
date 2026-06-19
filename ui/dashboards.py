"""Plotly-powered dashboards: Admin, Global, Stream, and Object views."""

import pandas as pd
import plotly.express as px
import streamlit as st

from services import stream_service, validation_service


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------
def render_admin_dashboard() -> None:
    st.header("Admin Dashboard")
    m = validation_service.global_metrics()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Streams", m["total_streams"])
    c2.metric("Total Objects", m["total_objects"])
    c3.metric("Total Functional Specs", _count_specs())

    c4, c5, c6 = st.columns(3)
    c4.metric("Total Validation Runs", m["total_runs"])
    c5.metric("Success Rate", f"{m['success_rate']}%")
    c6.metric("Failure Rate", f"{m['failure_rate']}%")

    st.divider()
    _render_stream_charts()


def _count_specs() -> int:
    from database.models import FunctionalSpec
    from database.session import get_session

    with get_session() as session:
        return session.query(FunctionalSpec).count()


# ---------------------------------------------------------------------------
# Global (BA) dashboard
# ---------------------------------------------------------------------------
def render_global_dashboard() -> None:
    st.header("Global Dashboard")
    m = validation_service.global_metrics()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Streams", m["total_streams"])
    c2.metric("Total Objects", m["total_objects"])
    c3.metric("Total Validations", m["total_runs"])
    c4.metric("Records Processed", m["total_records"])
    c5.metric("Overall Success Rate", f"{m['success_rate']}%")

    st.divider()
    _render_stream_charts()


def _render_stream_charts() -> None:
    data = validation_service.metrics_by_stream()
    df = pd.DataFrame(data)
    if df.empty or df["runs"].sum() == 0:
        st.info("No validation runs recorded yet. Charts will populate once validations run.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            px.bar(df, x="stream", y="runs", title="Validation Runs by Stream", text="runs"),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            px.bar(
                df,
                x="stream",
                y="success_rate",
                title="Success Rate by Stream (%)",
                text="success_rate",
                range_y=[0, 100],
            ),
            use_container_width=True,
        )
    st.plotly_chart(
        px.bar(df, x="stream", y="failed_records", title="Failed Records by Stream", text="failed_records"),
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Stream dashboard
# ---------------------------------------------------------------------------
def render_stream_dashboard(stream_id: int) -> None:
    data = validation_service.metrics_for_stream(stream_id)
    if not data:
        st.warning("Stream not found.")
        return

    st.subheader(f"Stream Dashboard — {data['stream']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Objects", data["total_objects"])
    c2.metric("Total Validations", data["total_runs"])
    c3.metric("Success Rate", f"{data['success_rate']}%")

    obj_df = pd.DataFrame(data["objects"])
    if obj_df.empty:
        st.info("No objects configured in this stream.")
        return

    st.markdown("**Object-wise breakdown**")
    st.dataframe(obj_df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            px.bar(
                obj_df,
                x="object",
                y="success_rate",
                title="Success Rate by Object (%)",
                text="success_rate",
                range_y=[0, 100],
            ),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            px.bar(
                obj_df,
                x="object",
                y="failed_records",
                title="Object-wise Failure Analysis",
                text="failed_records",
            ),
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Object dashboard
# ---------------------------------------------------------------------------
def render_object_dashboard(object_id: int) -> None:
    data = validation_service.metrics_for_object(object_id)
    if not data:
        st.warning("Object not found.")
        return

    st.subheader(f"Object Dashboard — {data['object']} ({data['stream']})")
    c1, c2 = st.columns(2)
    c1.metric("Total Runs", data["total_runs"])
    c2.metric("Success Rate", f"{data['success_rate']}%")

    trend_df = pd.DataFrame(data["trend"])
    if not trend_df.empty:
        st.markdown("**Trend Over Time**")
        st.plotly_chart(
            px.line(
                trend_df,
                x="run_date",
                y="success_rate",
                markers=True,
                title="Success Rate Trend (%)",
                range_y=[0, 100],
            ),
            use_container_width=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top Validation Failures (by field)**")
        tf = pd.DataFrame(data["top_failures"])
        if tf.empty:
            st.info("No failures recorded.")
        else:
            st.plotly_chart(
                px.bar(tf, x="count", y="field", orientation="h", title="Top Failing Fields"),
                use_container_width=True,
            )
    with col2:
        st.markdown("**Most Common Rule Violations**")
        tv = pd.DataFrame(data["top_violations"])
        if tv.empty:
            st.info("No violations recorded.")
        else:
            st.dataframe(tv, use_container_width=True)
