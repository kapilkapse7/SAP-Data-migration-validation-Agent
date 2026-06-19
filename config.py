"""Central configuration for the SAP Data Migration Governance Platform."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FS_STORAGE_DIR = DATA_DIR / "fs_documents"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"

for _dir in (DATA_DIR, OUTPUT_DIR, FS_STORAGE_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

SAMPLE_FS_PATH = SAMPLE_DATA_DIR / "mdm_fs.txt"
SAMPLE_PRELOAD_PATH = SAMPLE_DATA_DIR / "preload.xlsx"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'governance.db').as_posix()}")

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
ROLE_ADMIN = "Admin"
ROLE_FC = "Functional Consultant"
ROLE_BA = "Business Analyst"

ALL_ROLES = (ROLE_ADMIN, ROLE_FC, ROLE_BA)


def get_api_key() -> str | None:
    """Return the configured Gemini API key, if any."""
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def has_api_key() -> bool:
    """Return True if a Gemini API key is configured."""
    return bool(get_api_key())
