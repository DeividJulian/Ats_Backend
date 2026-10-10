from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.candidate import Candidate
from models.user import User
from schemas.auth import LoginInput, RegisterInput, TokenOut, UserOut
from services.auth import get_current_user
from services.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def token_for(user: User) -> TokenOut:
    return TokenOut(access_token=create_token(user.id, user.role), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión")
def login(data: LoginInput, db: Session = Depends(get_db)):
    """Devuelve un token de acceso válido por 12 horas y los datos del usuario."""
    user = db.query(User).filter(func.lower(User.email) == data.email.lower()).first()
    # Same message whether the email exists or not, so accounts can't be discovered
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tu usuario está desactivado")
    return token_for(user)


@router.post("/register", response_model=TokenOut, status_code=201, summary="Crear cuenta de candidato")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    """Registro abierto para candidatos: crea su perfil y su usuario, y deja la sesión iniciada."""
    email = data.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    if db.query(Candidate).filter(func.lower(Candidate.email) == email).first():
        raise HTTPException(
            status_code=409,
            detail="Ese correo ya está registrado como candidato. Pide al equipo de selección que te dé acceso.",
        )
    candidate = Candidate(name=data.name, email=email, phone=data.phone, resume_text="", skills=[])
    db.add(candidate)
    db.flush()
    user = User(
        name=data.name, email=email, password_hash=hash_password(data.password), role="candidate",
        candidate_id=candidate.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return token_for(user)


@router.get("/me", response_model=UserOut, summary="Usuario actual")
def me(user: User = Depends(get_current_user)):
    return user
