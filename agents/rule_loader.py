"""Rule Loader Agent (Business Analyst) — loads stored rules for a selected object."""

import logging

from services.fs_service import get_latest_rules
from state import MigrationState

logger = logging.getLogger(__name__)


def load_stored_rules(state: MigrationState) -> MigrationState:
    """
    Business Analyst pipeline node.
    Loads the latest approved MDM FS rules for the selected object from the database.
    """
    object_id = state.get("object_id")
    if not object_id:
        return {**state, "rules": {}, "error": "No object selected"}

    rules = get_latest_rules(object_id)
    if not rules:
        return {
            **state,
            "rules": {},
            "error": "No approved rules are configured for this object. Contact an Admin.",
        }

    logger.info("Loaded %d stored rules for object %s", len(rules), object_id)
    return {**state, "rules": rules, "error": ""}
