"""
Cryptographic and security utilities for AURA Cloud Backend.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False

    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False

    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])
    except (ValueError, TypeError):
        return False

    computed_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(computed_hash, expected_hash)


def generate_pairing_code(length: int = 8) -> str:
    alphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    raw = "".join(secrets.choice(alphabet) for _ in range(length))
    if length == 8:
        return f"{raw[:4]}-{raw[4:]}"
    return raw


def generate_secure_token(prefix: str = "aura_usr_") -> str:
    return f"{prefix}{secrets.token_urlsafe(36)}"


def generate_device_token() -> str:
    return f"aura_dev_{secrets.token_urlsafe(40)}"
