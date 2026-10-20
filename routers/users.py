from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import StaffUserCreate, UserOut, UserUpdate
from services.auth import admin_only

router = APIRouter(prefix="/users", tags=["Usuarios"])


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.get("", response_model=list[UserOut], summary="Listar usuarios")
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=201, summary="Crear administrador o reclutador")
def create_user(data: StaffUserCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if db.query(User).filter(func.lower(User.email) == data.email.lower()).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    # Unverified until the person enters with the code sent to that email
    user = User(name=data.name, email=data.email.lower(), role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut, summary="Actualizar usuario")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), me: User = Depends(admin_only)):
    """Cambia nombre, rol o activa/desactiva. Un administrador no puede quitarse permisos a sí mismo."""
    user = get_user_or_404(db, user_id)
    if user.id == me.id and (data.is_active is False or (data.role and data.role != "admin")):
        raise HTTPException(status_code=409, detail="No puedes desactivarte ni quitarte el rol de administrador")
    if data.role and user.role == "candidate":
        raise HTTPException(status_code=409, detail="El rol de un candidato no se puede cambiar")
    if data.name is not None:
        user.name = data.name
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", summary="Eliminar usuario")
def delete_user(user_id: int, db: Session = Depends(get_db), me: User = Depends(admin_only)):
    """Elimina la cuenta. Si es un candidato, su perfil y sus postulaciones se conservan."""
    user = get_user_or_404(db, user_id)
    if user.id == me.id:
        raise HTTPException(status_code=409, detail="No puedes eliminar tu propia cuenta")
    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado"}
