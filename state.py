"""LangGraph state definition for the SAP Data Migration Governance workflow."""

from typing import Any, Optional, TypedDict

import pandas as pd


class MigrationState(TypedDict, total=False):
    """Shared state passed between agents in the role-aware pipeline."""

    # Routing
    mode: str  # "admin" | "fc" | "ba"
    role: str

    # Context (for persistence / stored rules)
    object_id: Optional[int]
    user_id: Optional[int]
    fs_file_name: str
    fs_bytes: Optional[bytes]

    # Pipeline data
    fs_content: str
    rules: dict[str, dict[str, Any]]
    preload_df: Optional[pd.DataFrame]
    validation_results: list[dict[str, Any]]
    report_path: str
    email_draft: str
    error: str
    total_records: int
    passed_records: int
    failed_records: int

    # Admin store result
    stored_version: Optional[int]
