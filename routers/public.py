from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.candidate import Candidate
from models.job import Job
from schemas.portal import PublicJob, PublicSummary

router = APIRouter(prefix="/public", tags=["Público"])


@router.get("/jobs", response_model=list[PublicJob], summary="Vacantes abiertas")
def open_jobs(db: Session = Depends(get_db)):
    """Bolsa de empleo pública: solo vacantes abiertas, sin datos internos."""
    return db.query(Job).filter(Job.status == "open").order_by(Job.id.desc()).all()


@router.get("/jobs/{job_id}", response_model=PublicJob, summary="Detalle de una vacante abierta")
def open_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.status == "open").first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada o cerrada")
    return job


@router.get("/summary", response_model=PublicSummary, summary="Cifras generales")
def summary(db: Session = Depends(get_db)):
    """Cifras para la página de inicio."""
    return PublicSummary(
        open_jobs=db.query(Job).filter(Job.status == "open").count(),
        candidates=db.query(Candidate).count(),
        hires=db.query(Application).filter(Application.status == "hired").count(),
    )
