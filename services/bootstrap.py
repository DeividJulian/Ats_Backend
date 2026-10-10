"""Creates the first administrator from environment variables, so a fresh deployment can be managed."""
import logging
import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.user import User
from services.security import hash_password

logger = logging.getLogger("ats.bootstrap")


def ensure_admin(db: Session) -> None:
    """With ADMIN_EMAIL and ADMIN_PASSWORD set, creates that admin if the account doesn't exist yet."""
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or ""
    if not email or not password:
        return
    if len(password) < 8:
        logger.warning("ADMIN_PASSWORD debe tener al menos 8 caracteres: no se creó el administrador")
        return
    if db.query(User).filter(func.lower(User.email) == email).first():
        return
    db.add(User(
        name=os.getenv("ADMIN_NAME") or "Administrador", email=email, password_hash=hash_password(password), role="admin",
    ))
    db.commit()
    logger.info("Administrador inicial creado: %s", email)
