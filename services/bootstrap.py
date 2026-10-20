"""Creates the first administrator from environment variables, so a fresh deployment can be managed."""
import logging
import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.user import User

logger = logging.getLogger("ats.bootstrap")


def ensure_admin(db: Session) -> None:
    """With ADMIN_EMAIL set, creates that admin if the account doesn't exist yet.

    There is no password: the admin enters with a code sent to that email, so it must be a real inbox.
    """
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    if not email:
        return
    if db.query(User).filter(func.lower(User.email) == email).first():
        return
    db.add(User(name=os.getenv("ADMIN_NAME") or "Administrador", email=email, role="admin"))
    db.commit()
    logger.info("Administrador inicial creado: %s (entra con el código que llega a ese correo)", email)
