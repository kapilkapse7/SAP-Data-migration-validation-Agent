"""File parsing utilities for MDM FS and preload Excel uploads."""

import io
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_FS_PATH = PROJECT_ROOT / "sample_data" / "mdm_fs.txt"
SAMPLE_PRELOAD_PATH = PROJECT_ROOT / "sample_data" / "preload.xlsx"


def read_fs_content(raw: bytes, filename: str) -> str:
    """Read MDM Functional Specification content from uploaded file bytes."""
    if not raw:
        return ""

    name = filename.lower()

    if name.endswith((".txt", ".md", ".csv")):
        return raw.decode("utf-8", errors="replace")

    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
        return df.to_string(index=False)

    return raw.decode("utf-8", errors="replace")


def read_preload_excel(raw: bytes) -> pd.DataFrame:
    """Load preload Excel data from uploaded file bytes."""
    if not raw:
        raise ValueError("Preload file is empty")
    try:
        return pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    except Exception as exc:
        logger.exception("Failed to read preload Excel: %s", exc)
        raise ValueError(f"Could not read preload Excel file: {exc}") from exc


def load_sample_fs() -> str:
    """Load sample MDM Functional Specification text."""
    if not SAMPLE_FS_PATH.exists():
        raise FileNotFoundError(f"Sample MDM FS not found at {SAMPLE_FS_PATH}")
    return SAMPLE_FS_PATH.read_text(encoding="utf-8")


def load_sample_preload() -> pd.DataFrame:
    """Load sample preload Excel data."""
    if not SAMPLE_PRELOAD_PATH.exists():
        raise FileNotFoundError(
            f"Sample preload not found at {SAMPLE_PRELOAD_PATH}. "
            "Run: py sample_data/create_preload.py"
        )
    return pd.read_excel(SAMPLE_PRELOAD_PATH, engine="openpyxl")
