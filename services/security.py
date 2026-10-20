"""Signed session tokens (JWT HS256). The user behind the token is read again from the database on every request."""
from datetime import datetime, timedelta, timezone

import base64
import hashlib
import hmac
import secrets

import jwt

import config

TOKEN_ALGORITHM = "HS256"
# scrypt cost parameters (about 16 MB of memory per hash)
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "scrypt${}${}".format(base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return hmac.compare_digest(digest, expected)


def create_token(user_id: int, role: str, hours: float | None = None) -> str:
    now = datetime.now(timezone.utc)
    lifetime = timedelta(hours=config.TOKEN_HOURS if hours is None else hours)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, config.SECRET_KEY, algorithm=TOKEN_ALGORITHM)


def decode_token(token: str) -> int | None:
    """Returns the user id, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[TOKEN_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
