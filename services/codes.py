"""Passwordless login: one-time six-digit codes sent by email."""
import hashlib
import hmac
import math
import secrets
from datetime import datetime, timedelta, timezone
from html import escape

from sqlalchemy import func
from sqlalchemy.orm import Session

import config
from models.user import User, VerificationCode
from services.mailer import send_email


class CodeCooldown(Exception):
    def __init__(self, seconds: int):
        self.seconds = seconds
        super().__init__(f"Espera {seconds} segundos antes de pedir otro código")


class InvalidCode(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(moment: datetime) -> datetime:
    """SQLite returns dates without a time zone: they are UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _hash(user_id: int, code: str) -> str:
    # The user id in the message makes the same code hash differently for each account
    return hmac.new(config.SECRET_KEY.encode(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def find_user(db: Session, email: str) -> User | None:
    return db.query(User).filter(func.lower(User.email) == normalize_email(email)).first()


def _latest_code(db: Session, user: User, only_active: bool = False) -> VerificationCode | None:
    query = db.query(VerificationCode).filter(VerificationCode.user_id == user.id)
    if only_active:
        query = query.filter(VerificationCode.used.is_(False))
    return query.order_by(VerificationCode.id.desc()).first()


def issue_code(db: Session, user: User, purpose: str) -> str:
    """Creates a new code and invalidates the previous ones, respecting a minimum wait between emails."""
    latest = _latest_code(db, user)
    if latest:
        wait = config.CODE_WAIT_SECONDS - (utc_now() - _aware(latest.created_at)).total_seconds()
        if wait > 0:
            raise CodeCooldown(math.ceil(wait))

    db.query(VerificationCode).filter(
        VerificationCode.user_id == user.id, VerificationCode.used.is_(False)
    ).update({"used": True})
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        VerificationCode(
            user_id=user.id,
            code_hash=_hash(user.id, code),
            purpose=purpose,
            expires_at=utc_now() + timedelta(minutes=config.CODE_MINUTES),
        )
    )
    db.flush()
    return code


def check_code(db: Session, user: User, code: str) -> None:
    """Validates the latest active code. Raises InvalidCode; the caller must commit to keep the failed attempt."""
    record = _latest_code(db, user, only_active=True)
    if not record:
        raise InvalidCode("No hay un código activo: pide uno nuevo")
    if _aware(record.expires_at) < utc_now():
        record.used = True
        raise InvalidCode("El código venció: pide uno nuevo")
    if not hmac.compare_digest(record.code_hash, _hash(user.id, code)):
        record.attempts += 1
        left = config.CODE_ATTEMPTS - record.attempts
        if left <= 0:
            record.used = True
            raise InvalidCode("Código incorrecto. Agotaste los intentos: pide uno nuevo")
        raise InvalidCode(f"Código incorrecto. Te quedan {left} {'intento' if left == 1 else 'intentos'}")
    record.used = True


def finish_login(user: User) -> None:
    """After a correct code: the first time it activates the account."""
    user.verified = True
    user.last_login = utc_now()


def send_code(user: User, code: str, purpose: str) -> None:
    action = "activar tu cuenta" if purpose == "signup" else "iniciar sesión"
    subject = "Tu código para activar Portal ATS" if purpose == "signup" else "Tu código para entrar a Portal ATS"
    text = (
        f"Hola, {user.name}:\n\n"
        f"Usa este código para {action}: {code}\n\n"
        f"Vence en {config.CODE_MINUTES} minutos. Si no lo pediste, ignora este correo.\n\n"
        "Portal ATS"
    )
    html = (
        f"<p>Hola, {escape(user.name)}:</p>"
        f"<p>Usa este código para {action}:</p>"
        f'<p style="font-size:28px;font-weight:700;letter-spacing:6px">{code}</p>'
        f"<p>Vence en {config.CODE_MINUTES} minutos. Si no lo pediste, ignora este correo.</p>"
        "<p>Portal ATS</p>"
    )
    send_email(user.email, subject, text, html)
