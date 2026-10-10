"""Password hashing (scrypt, from the standard library) and signed access tokens (JWT)."""
import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

logger = logging.getLogger("ats.security")

TOKEN_ALGORITHM = "HS256"
TOKEN_HOURS = 12
# scrypt cost parameters (about 16 MB of memory per hash)
_N, _R, _P = 2**14, 8, 1


def _secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        # Without a configured secret, a random one keeps tokens safe; they just stop working after a restart
        secret = secrets.token_urlsafe(48)
        os.environ["JWT_SECRET"] = secret
        logger.warning("JWT_SECRET no está configurado: se generó uno temporal (las sesiones se cierran al reiniciar)")
    return secret


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


def create_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(hours=TOKEN_HOURS)}
    return jwt.encode(payload, _secret(), algorithm=TOKEN_ALGORITHM)


def decode_token(token: str) -> int | None:
    """Returns the user id, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[TOKEN_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
