"""FastAPI dependencies that identify the user behind a request and check their role."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.security import decode_token

ROLES = ("admin", "recruiter", "candidate")

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión", headers={"WWW-Authenticate": "Bearer"})
    user_id = decode_token(credentials.credentials)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(
            status_code=401, detail="La sesión no es válida o expiró; inicia sesión de nuevo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tu usuario está desactivado")
    return user


def require_roles(*roles: str):
    def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
        return user

    return check


# Shortcuts for the routers
staff_only = require_roles("admin", "recruiter")
admin_only = require_roles("admin")
candidate_only = require_roles("candidate")
