"""Functional Specification service — versioned storage and rule persistence."""

import json
import logging
from datetime import datetime
from pathlib import Path

from config import FS_STORAGE_DIR
from database.models import FunctionalSpec, ValidationRule
from database.session import get_session

logger = logging.getLogger(__name__)


def _next_version(session, object_id: int) -> int:
    """Compute the next version number for an object's FS."""
    latest = (
        session.query(FunctionalSpec)
        .filter(FunctionalSpec.object_id == object_id)
        .order_by(FunctionalSpec.version.desc())
        .first()
    )
    return (latest.version + 1) if latest else 1


def store_fs_version(
    object_id: int,
    file_name: str,
    raw_bytes: bytes,
    rules: dict,
) -> dict:
    """
    Persist a new FS version (file on disk + metadata + rules) for an object.
    Previous versions are deactivated; the new version becomes active/latest.
    Returns metadata about the created version.
    """
    with get_session() as session:
        version = _next_version(session, object_id)

        # Save the document file on disk
        safe_name = Path(file_name).name or "fs_document"
        stored_name = f"obj{object_id}_v{version}_{safe_name}"
        stored_path = FS_STORAGE_DIR / stored_name
        stored_path.write_bytes(raw_bytes)

        # Deactivate older versions
        session.query(FunctionalSpec).filter(
            FunctionalSpec.object_id == object_id
        ).update({FunctionalSpec.is_active: False})

        spec = FunctionalSpec(
            object_id=object_id,
            version=version,
            file_name=safe_name,
            file_path=str(stored_path),
            is_active=True,
            upload_date=datetime.utcnow(),
        )
        session.add(spec)
        session.flush()

        # Store extracted rules linked to this spec version
        session.add(
            ValidationRule(
                object_id=object_id,
                spec_id=spec.id,
                rule_json=json.dumps(rules, ensure_ascii=False),
            )
        )

        logger.info("Stored FS v%d for object %d (%d rules)", version, object_id, len(rules))
        return {
            "spec_id": spec.id,
            "version": version,
            "file_name": safe_name,
            "rule_count": len(rules),
        }


def list_fs_versions(object_id: int) -> list[dict]:
    """Return version history for an object's Functional Specifications."""
    with get_session() as session:
        specs = (
            session.query(FunctionalSpec)
            .filter(FunctionalSpec.object_id == object_id)
            .order_by(FunctionalSpec.version.desc())
            .all()
        )
        return [
            {
                "version": s.version,
                "file_name": s.file_name,
                "is_active": s.is_active,
                "upload_date": s.upload_date.strftime("%Y-%m-%d %H:%M:%S"),
                "rule_count": len(json.loads(s.rules[0].rule_json)) if s.rules else 0,
            }
            for s in specs
        ]


def get_latest_rules(object_id: int) -> dict:
    """
    Return the rules associated with the latest active FS version for an object.
    Returns an empty dict if none are configured.
    """
    with get_session() as session:
        spec = (
            session.query(FunctionalSpec)
            .filter(
                FunctionalSpec.object_id == object_id,
                FunctionalSpec.is_active.is_(True),
            )
            .order_by(FunctionalSpec.version.desc())
            .first()
        )
        if spec and spec.rules:
            return json.loads(spec.rules[-1].rule_json)

        # Fallback: any latest rule row for the object
        rule = (
            session.query(ValidationRule)
            .filter(ValidationRule.object_id == object_id)
            .order_by(ValidationRule.created_at.desc())
            .first()
        )
        return json.loads(rule.rule_json) if rule else {}


def has_rules(object_id: int) -> bool:
    """Return True if the object has any configured rules."""
    return bool(get_latest_rules(object_id))
