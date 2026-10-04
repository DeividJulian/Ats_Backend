from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.candidato import Candidato
from models.postulacion import Postulacion
from schemas.candidato import CandidatoCreate, CandidatoOut
from services.habilidades import canonizar_habilidades, extraer_habilidades
from services.perfil import extraer_anios_experiencia, extraer_nivel_educacion

router = APIRouter(prefix="/candidatos", tags=["Candidatos"])


def completar_perfil(candidato: Candidato, datos: CandidatoCreate) -> None:
    """Combina lo que escribió el reclutador con lo que el sistema detecta en la hoja de vida."""
    candidato.nombre = datos.nombre
    candidato.email = datos.email
    candidato.telefono = datos.telefono
    candidato.cv_texto = datos.cv_texto
    candidato.habilidades = sorted(set(canonizar_habilidades(datos.habilidades)) | set(extraer_habilidades(datos.cv_texto)))
    candidato.anios_experiencia = (
        datos.anios_experiencia if datos.anios_experiencia is not None else extraer_anios_experiencia(datos.cv_texto)
    )
    candidato.nivel_educacion = datos.nivel_educacion or extraer_nivel_educacion(datos.cv_texto)


def correo_en_uso(db: Session, email: str, excluir_id: int | None = None) -> bool:
    consulta = db.query(Candidato).filter(func.lower(Candidato.email) == email.lower())
    if excluir_id is not None:
        consulta = consulta.filter(Candidato.id != excluir_id)
    return consulta.first() is not None


def obtener_candidato(db: Session, candidato_id: int) -> Candidato:
    candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    return candidato


@router.post("", response_model=CandidatoOut, status_code=201)
def crear_candidato(datos: CandidatoCreate, db: Session = Depends(get_db)):
    if correo_en_uso(db, datos.email):
        raise HTTPException(status_code=409, detail="Ya existe un candidato con ese correo")
    candidato = Candidato()
    completar_perfil(candidato, datos)
    db.add(candidato)
    db.commit()
    db.refresh(candidato)
    return candidato


@router.get("", response_model=list[CandidatoOut])
def listar_candidatos(habilidad: str | None = None, db: Session = Depends(get_db)):
    candidatos = db.query(Candidato).order_by(Candidato.id).all()
    if habilidad:
        buscada = canonizar_habilidades([habilidad])
        if buscada:
            candidatos = [c for c in candidatos if buscada[0] in (c.habilidades or [])]
    return candidatos


@router.get("/{candidato_id}", response_model=CandidatoOut)
def obtener(candidato_id: int, db: Session = Depends(get_db)):
    return obtener_candidato(db, candidato_id)


@router.put("/{candidato_id}", response_model=CandidatoOut)
def actualizar_candidato(candidato_id: int, datos: CandidatoCreate, db: Session = Depends(get_db)):
    candidato = obtener_candidato(db, candidato_id)
    if correo_en_uso(db, datos.email, excluir_id=candidato_id):
        raise HTTPException(status_code=409, detail="Ya existe otro candidato con ese correo")
    completar_perfil(candidato, datos)
    db.commit()
    db.refresh(candidato)
    return candidato


@router.delete("/{candidato_id}")
def eliminar_candidato(candidato_id: int, db: Session = Depends(get_db)):
    candidato = obtener_candidato(db, candidato_id)
    borradas = db.query(Postulacion).filter(Postulacion.candidato_id == candidato_id).delete()
    db.delete(candidato)
    db.commit()
    return {"mensaje": "Candidato eliminado", "postulaciones_eliminadas": borradas}
