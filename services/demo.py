"""Demo accounts that enter with a shared password, for presentations.

Only usable with DEMO_LOGIN=true. Their Gmail inboxes are not ours, so they never receive emails:
the code login refuses them and they always enter with the password.
"""
import hmac
import logging

from sqlalchemy.orm import Session

import config
from models.candidate import Candidate
from models.user import User
from services.codes import find_user, normalize_email

logger = logging.getLogger("ats.demo")

DEMO_PASSWORD = "demo 123"
# email -> (name, role)
DEMO_ACCOUNTS = {
    "administrador@gmail.com": ("Administrador Demo", "admin"),
    "usuario@gmail.com": ("Usuario Demo", "candidate"),
}


def is_demo_email(email: str) -> bool:
    return normalize_email(email) in DEMO_ACCOUNTS


def password_matches(password: str) -> bool:
    return hmac.compare_digest(password.encode(), DEMO_PASSWORD.encode())


def get_or_create_demo_user(db: Session, email: str) -> User:
    """Returns the demo account, creating it (and the candidate profile, if it needs one) the first time."""
    email = normalize_email(email)
    user = find_user(db, email)
    if user:
        return user
    name, role = DEMO_ACCOUNTS[email]
    candidate_id = None
    if role == "candidate":
        candidate = Candidate(name=name, email=email, phone=None, resume_text="", skills=[])
        db.add(candidate)
        db.flush()
        candidate_id = candidate.id
    user = User(name=name, email=email, role=role, candidate_id=candidate_id, verified=True)
    db.add(user)
    db.flush()
    return user


def ensure_demo_accounts(db: Session) -> None:
    """With DEMO_LOGIN on, the demo accounts exist from startup."""
    if not config.DEMO_LOGIN:
        return
    for email in DEMO_ACCOUNTS:
        get_or_create_demo_user(db, email)
    db.commit()
    logger.info("Acceso demo activo: %s", ", ".join(DEMO_ACCOUNTS))
