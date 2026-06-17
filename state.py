"""LangGraph state definition for the SAP Data Migration Validation workflow."""

from typing import Any, Optional, TypedDict

import pandas as pd


class MigrationState(TypedDict, total=False):
    """Shared state passed between agents in the validation pipeline."""

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
