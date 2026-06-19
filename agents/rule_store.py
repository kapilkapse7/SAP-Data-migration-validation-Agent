"""Rule Store Agent (Admin) — persists extracted rules + FS version to the database."""

import logging

from services.fs_service import store_fs_version
from state import MigrationState

logger = logging.getLogger(__name__)


def store_rules(state: MigrationState) -> MigrationState:
    """
    Admin pipeline node.
    Persists the uploaded FS document (new version) and its extracted rules.
    """
    object_id = state.get("object_id")
    rules = state.get("rules", {})

    if not object_id:
        return {**state, "error": "No object selected for rule storage"}
    if not rules:
        return {**state, "error": "No rules extracted; nothing to store"}

    try:
        meta = store_fs_version(
            object_id=object_id,
            file_name=state.get("fs_file_name", "fs_document.txt"),
            raw_bytes=state.get("fs_bytes") or state.get("fs_content", "").encode("utf-8"),
            rules=rules,
        )
        logger.info("Stored rules for object %s as version %s", object_id, meta["version"])
        return {**state, "stored_version": meta["version"], "error": ""}
    except Exception as exc:
        logger.exception("Failed to store rules: %s", exc)
        return {**state, "error": f"Failed to store rules: {exc}"}
