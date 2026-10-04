from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.job import Job
from schemas.job import JobCreate, JobOut, JobStatus
from services.skills import canonicalize_skills, extract_skills

router = APIRouter(prefix="/vacantes", tags=["Vacantes"])

JobId = Path(alias="vacante_id")


def apply_data(job: Job, data: JobCreate) -> None:
    job.title = data.title
    job.description = data.description
    job.requirements = data.requirements
    job.min_experience_years = data.min_experience_years
    job.min_education_level = data.min_education_level

    skills = canonicalize_skills(data.required_skills)
    if not skills:
        # If the recruiter doesn't list them, the system infers them from the job text
        skills = extract_skills(f"{data.title}\n{data.description}\n{data.requirements}")
    job.required_skills = skills


def get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return job


@router.post("", response_model=JobOut, status_code=201, summary="Crear vacante")
def create_job(data: JobCreate, db: Session = Depends(get_db)):
    job = Job()
    apply_data(job, data)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut], summary="Listar vacantes")
def list_jobs(status: str | None = Query(None, alias="estado"), db: Session = Depends(get_db)):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    return query.order_by(Job.id.desc()).all()


@router.get("/{vacante_id}", response_model=JobOut, summary="Obtener vacante")
def get_job(job_id: int = JobId, db: Session = Depends(get_db)):
    return get_job_or_404(db, job_id)


@router.put("/{vacante_id}", response_model=JobOut, summary="Actualizar vacante")
def update_job(data: JobCreate, job_id: int = JobId, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    apply_data(job, data)
    db.commit()
    db.refresh(job)
    return job


@router.patch("/{vacante_id}/estado", response_model=JobOut, summary="Cambiar estado de la vacante")
def change_status(data: JobStatus, job_id: int = JobId, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    job.status = data.status
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{vacante_id}", summary="Eliminar vacante")
def delete_job(job_id: int = JobId, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    # Applications depend on the job, so they are deleted along with it
    deleted = db.query(Application).filter(Application.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    return {"mensaje": "Vacante eliminada", "postulaciones_eliminadas": deleted}
