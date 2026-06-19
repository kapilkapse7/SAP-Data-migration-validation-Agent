"""Password hashing utilities (stdlib PBKDF2 — no external dependency)."""

import hashlib
import hmac
import os

_ALGO = "sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash encoded as 'algo$iterations$salt$hash'."""
    salt = os.urandom(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(_ALGO, password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash."""
    try:
        algo, iterations, salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        derived = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(derived.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False
