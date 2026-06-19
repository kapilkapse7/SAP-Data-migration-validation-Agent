"""Authentication service — login, user lookup, and user management."""

import logging
from dataclasses import dataclass

from config import ALL_ROLES
from auth.security import hash_password, verify_password
from database.models import User
from database.session import get_session

logger = logging.getLogger(__name__)


@dataclass
class CurrentUser:
    """Lightweight, session-safe representation of the logged-in user."""

    id: int
    username: str
    role: str


def authenticate(username: str, password: str) -> CurrentUser | None:
    """Validate credentials and return the user, or None on failure."""
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user and verify_password(password, user.password_hash):
            logger.info("User '%s' authenticated as %s", username, user.role)
            return CurrentUser(id=user.id, username=user.username, role=user.role)
    logger.warning("Failed login attempt for '%s'", username)
    return None


def create_user(username: str, password: str, role: str) -> CurrentUser:
    """Create a new user. Raises ValueError on validation/uniqueness errors."""
    if role not in ALL_ROLES:
        raise ValueError(f"Invalid role: {role}")
    with get_session() as session:
        if session.query(User).filter(User.username == username).first():
            raise ValueError(f"User '{username}' already exists")
        user = User(username=username, password_hash=hash_password(password), role=role)
        session.add(user)
        session.flush()
        return CurrentUser(id=user.id, username=user.username, role=user.role)


def list_users() -> list[CurrentUser]:
    """Return all users (without password hashes)."""
    with get_session() as session:
        return [
            CurrentUser(id=u.id, username=u.username, role=u.role)
            for u in session.query(User).order_by(User.username).all()
        ]
