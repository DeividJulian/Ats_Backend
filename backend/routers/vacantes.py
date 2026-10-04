from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.postulacion import Postulacion
from models.vacante import Vacante
from schemas.vacante import VacanteCreate, VacanteEstado, VacanteOut
from services.habilidades import canonizar_habilidades, extraer_habilidades

router = APIRouter(prefix="/vacantes", tags=["Vacantes"])


def aplicar_datos(vacante: Vacante, datos: VacanteCreate) -> None:
    vacante.titulo = datos.titulo
    vacante.descripcion = datos.descripcion
    vacante.requisitos = datos.requisitos
    vacante.experiencia_minima_anios = datos.experiencia_minima_anios
    vacante.nivel_educacion_minimo = datos.nivel_educacion_minimo

    habilidades = canonizar_habilidades(datos.habilidades_requeridas)
    if not habilidades:
        # Si el reclutador no las escribe, el sistema las deduce del texto de la vacante
        habilidades = extraer_habilidades(f"{datos.titulo}\n{datos.descripcion}\n{datos.requisitos}")
    vacante.habilidades_requeridas = habilidades


def obtener_vacante(db: Session, vacante_id: int) -> Vacante:
    vacante = db.query(Vacante).filter(Vacante.id == vacante_id).first()
    if not vacante:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return vacante


@router.post("", response_model=VacanteOut, status_code=201)
def crear_vacante(datos: VacanteCreate, db: Session = Depends(get_db)):
    vacante = Vacante()
    aplicar_datos(vacante, datos)
    db.add(vacante)
    db.commit()
    db.refresh(vacante)
    return vacante


@router.get("", response_model=list[VacanteOut])
def listar_vacantes(estado: str | None = None, db: Session = Depends(get_db)):
    consulta = db.query(Vacante)
    if estado:
        consulta = consulta.filter(Vacante.estado == estado)
    return consulta.order_by(Vacante.id.desc()).all()


@router.get("/{vacante_id}", response_model=VacanteOut)
def obtener(vacante_id: int, db: Session = Depends(get_db)):
    return obtener_vacante(db, vacante_id)


@router.put("/{vacante_id}", response_model=VacanteOut)
def actualizar_vacante(vacante_id: int, datos: VacanteCreate, db: Session = Depends(get_db)):
    vacante = obtener_vacante(db, vacante_id)
    aplicar_datos(vacante, datos)
    db.commit()
    db.refresh(vacante)
    return vacante


@router.patch("/{vacante_id}/estado", response_model=VacanteOut)
def cambiar_estado(vacante_id: int, datos: VacanteEstado, db: Session = Depends(get_db)):
    vacante = obtener_vacante(db, vacante_id)
    vacante.estado = datos.estado
    db.commit()
    db.refresh(vacante)
    return vacante


@router.delete("/{vacante_id}")
def eliminar_vacante(vacante_id: int, db: Session = Depends(get_db)):
    vacante = obtener_vacante(db, vacante_id)
    # Las postulaciones dependen de la vacante, así que se eliminan con ella
    borradas = db.query(Postulacion).filter(Postulacion.vacante_id == vacante_id).delete()
    db.delete(vacante)
    db.commit()
    return {"mensaje": "Vacante eliminada", "postulaciones_eliminadas": borradas}
