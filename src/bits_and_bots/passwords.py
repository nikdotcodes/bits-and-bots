"""Password hashing with a stdlib scrypt format and legacy bcrypt verification."""

import base64
import hashlib
import hmac
import os

from passlib.context import CryptContext

_legacy = CryptContext(schemes=["bcrypt"], deprecated="auto")
_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_LEN = 32


def hash_password(password: str) -> str:
    # New account provisioning enforces 12+ characters. This primitive also
    # supports rehashing existing legacy credentials during successful login.
    if not password or len(password) > 1024:
        raise ValueError("Passwords must contain between 1 and 1024 characters")
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_LEN,
        maxmem=64 * 1024 * 1024,
    )
    return f"scrypt${_SCRYPT_N}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> tuple[bool, bool]:
    """Return (valid, needs_rehash). Supports existing bcrypt hashes."""
    if len(password) > 1024:
        return False, False
    if encoded.startswith("scrypt$"):
        try:
            _, n, salt64, digest64 = encoded.split("$", 3)
            n_value = int(n)
            if n_value < 2**14 or n_value > 2**17 or n_value & (n_value - 1):
                return False, False
            salt = base64.urlsafe_b64decode(salt64.encode())
            expected = base64.urlsafe_b64decode(digest64.encode())
            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=n_value,
                r=_SCRYPT_R,
                p=_SCRYPT_P,
                dklen=len(expected),
                maxmem=64 * 1024 * 1024,
            )
            return hmac.compare_digest(actual, expected), False
        except ValueError, TypeError:
            return False, False
    try:
        valid = bool(encoded) and _legacy.verify(password, encoded)
        return valid, valid
    except Exception: # noqa: BLE001
        return False, False
