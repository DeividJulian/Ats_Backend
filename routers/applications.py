from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.candidate import Candidate
from models.job import Job
from schemas.application import ApplicationCreate, ApplicationOut, ApplicationStatus
from services.matching import evaluate
from services.pipeline import is_valid_transition, next_statuses

router = APIRouter(prefix="/postulaciones", tags=["Postulaciones"])

ApplicationId = Path(alias="postulacion_id")


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")
    return application


@router.post("", response_model=ApplicationOut, status_code=201, summary="Postular candidato")
def apply(data: ApplicationCreate, db: Session = Depends(get_db)):
    """Postula un candidato a una vacante y calcula su puntaje de ajuste al instante."""
    job = db.query(Job).filter(Job.id == data.job_id).first()
    candidate = db.query(Candidate).filter(Candidate.id == data.candidate_id).first()
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Vacante o candidato no encontrado")
    if job.status != "abierta":
        raise HTTPException(status_code=409, detail="La vacante está cerrada y no recibe postulaciones")

    already_applied = (
        db.query(Application)
        .filter(Application.job_id == data.job_id, Application.candidate_id == data.candidate_id)
        .first()
    )
    if already_applied:
        raise HTTPException(status_code=409, detail="El candidato ya está postulado a esta vacante")

    result = evaluate(db, job, candidate)
    application = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        score=result["score"],
        details=result,
        status="nuevo",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=list[ApplicationOut], summary="Listar postulaciones")
def list_applications(
    job_id: int | None = Query(None, alias="vacante_id"),
    candidate_id: int | None = Query(None, alias="candidato_id"),
    status: str | None = Query(None, alias="estado"),
    db: Session = Depends(get_db),
):
    query = db.query(Application)
    if job_id is not None:
        query = query.filter(Application.job_id == job_id)
    if candidate_id is not None:
        query = query.filter(Application.candidate_id == candidate_id)
    if status:
        query = query.filter(Application.status == status)
    return query.order_by(Application.score.desc()).all()


@router.get("/{postulacion_id}", response_model=ApplicationOut, summary="Obtener postulación")
def get_application(application_id: int = ApplicationId, db: Session = Depends(get_db)):
    return get_application_or_404(db, application_id)


@router.patch("/{postulacion_id}/estado", response_model=ApplicationOut, summary="Cambiar estado de la postulación")
def change_status(data: ApplicationStatus, application_id: int = ApplicationId, db: Session = Depends(get_db)):
    """Avanza la postulación en el flujo: nuevo, preseleccionado, entrevista, oferta, contratado (o rechazado)."""
    application = get_application_or_404(db, application_id)
    if not is_valid_transition(application.status, data.status):
        allowed = next_statuses(application.status)
        detail = f"No se puede pasar de '{application.status}' a '{data.status}'. " + (
            f"Estados permitidos: {', '.join(allowed)}." if allowed else "Este estado es final."
        )
        raise HTTPException(status_code=409, detail=detail)
    application.status = data.status
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{postulacion_id}", summary="Retirar postulación")
def withdraw_application(application_id: int = ApplicationId, db: Session = Depends(get_db)):
    application = get_application_or_404(db, application_id)
    db.delete(application)
    db.commit()
    return {"mensaje": "Postulación eliminada"}
