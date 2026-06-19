"""Seed the database with default users, streams, and migration objects.

Run once after first install:

    python -m database.seed
"""

import logging

from config import ROLE_ADMIN, ROLE_BA, ROLE_FC
from auth.security import hash_password
from database.models import MigrationObject, Stream, User
from database.session import get_session, init_db

logger = logging.getLogger(__name__)

DEFAULT_USERS = [
    ("admin", "admin123", ROLE_ADMIN),
    ("snehit", "snehit123", ROLE_ADMIN),
    ("consultant", "fc123", ROLE_FC),
    ("analyst", "ba123", ROLE_BA),
]

# Stream -> list of objects
DEFAULT_HIERARCHY = {
    "O2C": ["Business Partner", "CMIR", "Pricing Conditions", "Customer Master"],
    "P2P": ["Vendor Master", "Purchase Info Record", "Source List"],
    "R2R": ["Cost Center", "Profit Center", "GL Master"],
    "MDG": [],
    "SCM": [],
}


def seed_users() -> None:
    with get_session() as session:
        for username, password, role in DEFAULT_USERS:
            if not session.query(User).filter(User.username == username).first():
                session.add(
                    User(username=username, password_hash=hash_password(password), role=role)
                )
                logger.info("Created user '%s' (%s)", username, role)


def seed_streams_and_objects() -> None:
    with get_session() as session:
        for stream_name, objects in DEFAULT_HIERARCHY.items():
            stream = session.query(Stream).filter(Stream.stream_name == stream_name).first()
            if not stream:
                stream = Stream(stream_name=stream_name)
                session.add(stream)
                session.flush()
                logger.info("Created stream '%s'", stream_name)
            for obj_name in objects:
                exists = (
                    session.query(MigrationObject)
                    .filter(
                        MigrationObject.stream_id == stream.id,
                        MigrationObject.object_name == obj_name,
                    )
                    .first()
                )
                if not exists:
                    session.add(MigrationObject(stream_id=stream.id, object_name=obj_name))
                    logger.info("  + object '%s'", obj_name)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    init_db()
    seed_users()
    seed_streams_and_objects()
    print("\nSeed complete. Default logins:")
    print("  Admin               -> username: admin       password: admin123")
    print("  Functional Consultant -> username: consultant password: fc123")
    print("  Business Analyst    -> username: analyst     password: ba123")


if __name__ == "__main__":
    main()
