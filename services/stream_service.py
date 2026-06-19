"""Stream and Migration Object management service."""

import logging

from database.models import MigrationObject, Stream
from database.session import get_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------
def create_stream(stream_name: str, description: str = "") -> int:
    """Create a stream and return its id. Raises ValueError if duplicate."""
    name = stream_name.strip()
    if not name:
        raise ValueError("Stream name cannot be empty")
    with get_session() as session:
        if session.query(Stream).filter(Stream.stream_name == name).first():
            raise ValueError(f"Stream '{name}' already exists")
        stream = Stream(stream_name=name, description=description.strip())
        session.add(stream)
        session.flush()
        return stream.id


def list_streams() -> list[dict]:
    """Return all streams as dicts with object counts."""
    with get_session() as session:
        streams = session.query(Stream).order_by(Stream.stream_name).all()
        return [
            {
                "id": s.id,
                "stream_name": s.stream_name,
                "description": s.description,
                "object_count": len(s.objects),
            }
            for s in streams
        ]


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------
def create_object(stream_id: int, object_name: str, description: str = "") -> int:
    """Create a migration object under a stream. Raises ValueError if duplicate."""
    name = object_name.strip()
    if not name:
        raise ValueError("Object name cannot be empty")
    with get_session() as session:
        if not session.get(Stream, stream_id):
            raise ValueError("Stream does not exist")
        exists = (
            session.query(MigrationObject)
            .filter(
                MigrationObject.stream_id == stream_id,
                MigrationObject.object_name == name,
            )
            .first()
        )
        if exists:
            raise ValueError(f"Object '{name}' already exists in this stream")
        obj = MigrationObject(stream_id=stream_id, object_name=name, description=description.strip())
        session.add(obj)
        session.flush()
        return obj.id


def list_objects(stream_id: int) -> list[dict]:
    """Return objects belonging to a stream."""
    with get_session() as session:
        objects = (
            session.query(MigrationObject)
            .filter(MigrationObject.stream_id == stream_id)
            .order_by(MigrationObject.object_name)
            .all()
        )
        return [
            {
                "id": o.id,
                "object_name": o.object_name,
                "description": o.description,
                "spec_count": len(o.functional_specs),
            }
            for o in objects
        ]


def get_object(object_id: int) -> dict | None:
    """Return a single object with its stream name, or None."""
    with get_session() as session:
        obj = session.get(MigrationObject, object_id)
        if not obj:
            return None
        return {
            "id": obj.id,
            "object_name": obj.object_name,
            "stream_id": obj.stream_id,
            "stream_name": obj.stream.stream_name,
            "description": obj.description,
        }
