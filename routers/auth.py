from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.candidate import Candidate
from models.user import User
import config
from schemas.auth import CodeSent, DemoLoginInput, DemoStatus, LoginInput, RegisterInput, TokenOut, UserOut, VerifyInput
from services.auth import get_current_user
from services import demo
from services.codes import (
    CodeCooldown,
    InvalidCode,
    check_code,
    find_user,
    finish_login,
    issue_code,
    normalize_email,
    send_code,
)
from services.mailer import MailError
from services.security import create_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def token_for(user: User) -> TokenOut:
    return TokenOut(access_token=create_token(user.id, user.role), user=UserOut.model_validate(user))


DEMO_ONLY_PASSWORD = "Es una cuenta demo: entra con su contraseña"


def _send_new_code(db: Session, user: User, purpose: str) -> None:
    """Creates and emails the code. If the email doesn't go out, everything is undone (no half-made account)."""
    if demo.is_demo_email(user.email):
        # Those inboxes are not ours: they never get an email
        db.rollback()
        raise HTTPException(status_code=409, detail=DEMO_ONLY_PASSWORD)
    try:
        code = issue_code(db, user, purpose)
    except CodeCooldown as e:
        db.rollback()
        raise HTTPException(status_code=429, detail=str(e), headers={"Retry-After": str(e.seconds)})
    try:
        send_code(user, code, purpose)
    except MailError:
        db.rollback()
        raise HTTPException(status_code=502, detail="No pudimos enviar el correo. Inténtalo de nuevo en unos minutos.")
    db.commit()


@router.post("/register", response_model=CodeSent, status_code=201, summary="Crear cuenta de candidato")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    """Open sign-up for candidates: creates the account without verifying and emails a code.

    If the account exists but was never verified, the code is sent again. A candidate profile created
    earlier by a recruiter with the same email is linked: the code proves the email belongs to them.
    """
    email = normalize_email(data.email)
    if demo.is_demo_email(email):
        raise HTTPException(status_code=409, detail=DEMO_ONLY_PASSWORD)
    user = find_user(db, email)
    if user and user.verified:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo: inicia sesión")
    if user and user.role != "candidate":
        raise HTTPException(status_code=409, detail="Ese correo pertenece al equipo de selección: inicia sesión")
    if user:
        user.name = data.name
        if user.candidate:
            user.candidate.name = data.name
            user.candidate.phone = data.phone or user.candidate.phone
    else:
        candidate = db.query(Candidate).filter(func.lower(Candidate.email) == email).first()
        if candidate is None:
            candidate = Candidate(name=data.name, email=email, phone=data.phone, resume_text="", skills=[])
            db.add(candidate)
            db.flush()
        elif db.query(User).filter(User.candidate_id == candidate.id).first():
            raise HTTPException(status_code=409, detail="Ese perfil ya tiene una cuenta: inicia sesión")
        user = User(name=data.name, email=email, role="candidate", candidate_id=candidate.id)
        db.add(user)
        db.flush()
    _send_new_code(db, user, "signup")
    return CodeSent(message="Te enviamos un código para activar tu cuenta", email=user.email)


@router.post("/login", response_model=CodeSent, summary="Pedir código para entrar")
def login(data: LoginInput, db: Session = Depends(get_db)):
    """Emails a one-time login code."""
    user = find_user(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="No hay una cuenta con ese correo: crea una primero")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tu usuario está desactivado")
    _send_new_code(db, user, "login")
    return CodeSent(message="Te enviamos un código para entrar", email=user.email)


@router.post("/verify", response_model=TokenOut, summary="Entrar con el código")
def verify(data: VerifyInput, db: Session = Depends(get_db)):
    """Checks the emailed code and returns the session token. The first time it activates the account."""
    user = find_user(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="No hay un código activo: pide uno nuevo")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tu usuario está desactivado")
    try:
        check_code(db, user, data.code)
    except InvalidCode as e:
        db.commit()  # keeps the failed attempt or the invalidated code
        raise HTTPException(status_code=400, detail=str(e))
    finish_login(user)
    db.commit()
    db.refresh(user)
    return token_for(user)


@router.get("/demo", response_model=DemoStatus, summary="¿Está activo el acceso demo?")
def demo_status():
    return DemoStatus(enabled=config.DEMO_LOGIN)


@router.post("/demo-login", response_model=TokenOut, summary="Entrar con una cuenta demo")
def demo_login(data: DemoLoginInput, db: Session = Depends(get_db)):
    """Only the demo accounts, only with DEMO_LOGIN=true. Everyone else enters with the emailed code."""
    if not config.DEMO_LOGIN:
        raise HTTPException(status_code=404, detail="El acceso demo está desactivado")
    if not demo.is_demo_email(data.email) or not demo.password_matches(data.password):
        raise HTTPException(status_code=401, detail="Correo o contraseña de la cuenta demo incorrectos")
    user = demo.get_or_create_demo_user(db, data.email)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tu usuario está desactivado")
    finish_login(user)
    db.commit()
    db.refresh(user)
    return token_for(user)


@router.get("/me", response_model=UserOut, summary="Usuario actual")
def me(user: User = Depends(get_current_user)):
    return user
