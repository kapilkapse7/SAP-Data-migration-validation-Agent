"""Audit trail service — records significant user actions."""

import logging

from database.models import AuditLog
from database.session import get_session

logger = logging.getLogger(__name__)


def log_action(user, action: str, detail: str = "") -> None:
    """Persist an audit log entry. `user` may be a CurrentUser or None."""
    try:
        with get_session() as session:
            session.add(
                AuditLog(
                    user_id=getattr(user, "id", None),
                    username=getattr(user, "username", "system"),
                    role=getattr(user, "role", ""),
                    action=action,
                    detail=detail,
                )
            )
        logger.info("AUDIT | %s | %s | %s", getattr(user, "username", "system"), action, detail)
    except Exception as exc:  # auditing must never break the main flow
        logger.exception("Failed to write audit log: %s", exc)


def list_recent(limit: int = 200) -> list[dict]:
    """Return recent audit entries as dicts, newest first."""
    with get_session() as session:
        rows = (
            session.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "Timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "User": r.username,
                "Role": r.role,
                "Action": r.action,
                "Detail": r.detail,
            }
            for r in rows
        ]
