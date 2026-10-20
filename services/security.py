"""Signed session tokens (JWT HS256). The user behind the token is read again from the database on every request."""
from datetime import datetime, timedelta, timezone

import jwt

import config

TOKEN_ALGORITHM = "HS256"


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
