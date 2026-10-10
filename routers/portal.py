from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.candidate import Candidate
from models.job import Job
from models.user import User
from routers.applications import create_application
from routers.resumes import read_pdf_or_422
from schemas.application import JobRecommendation
from schemas.candidate import CandidateOut
from schemas.insights import CandidateInsights
from schemas.portal import ApplyInput, MyApplication, ProfileUpdate
from services.auth import candidate_only
from services.insights import candidate_insights
from services.matching import recommend_jobs
from services.profile import extract_education_level, extract_experience_years
from services.resume import apply_resume_text
from services.skills import canonicalize_skills, extract_skills, sort_skills

router = APIRouter(prefix="/me", tags=["Portal del candidato"])


def my_profile(user: User, db: Session) -> Candidate:
    candidate = db.get(Candidate, user.candidate_id) if user.candidate_id else None
    if not candidate:
        raise HTTPException(status_code=404, detail="Tu perfil de candidato no existe")
    return candidate


def to_my_application(a: Application) -> MyApplication:
    details = a.details or {}
    return MyApplication(
        id=a.id, job_id=a.job_id, job_title=a.job.title, job_status=a.job.status, status=a.status,
        matching_skills=details.get("matching_skills", []), missing_skills=details.get("missing_skills", []),
        created_at=a.created_at,
    )


@router.get("/profile", response_model=CandidateOut, summary="Mi perfil")
def get_profile(user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    return my_profile(user, db)


@router.put("/profile", response_model=CandidateOut, summary="Actualizar mi perfil")
def update_profile(data: ProfileUpdate, user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    """Lo que no se indique (experiencia, nivel educativo) se deduce del texto de la hoja de vida."""
    candidate = my_profile(user, db)
    candidate.name = user.name = data.name
    candidate.phone = data.phone
    candidate.resume_text = data.resume_text
    candidate.skills = sort_skills(canonicalize_skills(data.skills) + extract_skills(data.resume_text))
    candidate.experience_years = (
        data.experience_years if data.experience_years is not None else extract_experience_years(data.resume_text)
    )
    candidate.education_level = data.education_level or extract_education_level(data.resume_text)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/resume", response_model=CandidateOut, summary="Subir mi hoja de vida en PDF")
async def upload_my_resume(
    file: UploadFile = File(...), user: User = Depends(candidate_only), db: Session = Depends(get_db)
):
    candidate = my_profile(user, db)
    apply_resume_text(candidate, await read_pdf_or_422(file))
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/insights", response_model=CandidateInsights, summary="Mi análisis de perfil")
def my_insights(user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    """Resumen de tu perfil y qué te conviene aprender según las vacantes abiertas."""
    candidate = my_profile(user, db)
    open_jobs = db.query(Job).filter(Job.status == "open").all()
    insights = candidate_insights(
        candidate.skills or [], candidate.experience_years or 0, candidate.education_level,
        [j.required_skills or [] for j in open_jobs],
    )
    return CandidateInsights(candidate_id=candidate.id, name=candidate.name, **insights)


@router.get("/recommended-jobs", response_model=list[JobRecommendation], summary="Vacantes recomendadas para mí")
def my_recommended_jobs(
    limit: int = Query(default=5, ge=1, le=50), user: User = Depends(candidate_only), db: Session = Depends(get_db)
):
    return recommend_jobs(db, my_profile(user, db), limit)


@router.get("/applications", response_model=list[MyApplication], summary="Mis postulaciones")
def my_applications(user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    candidate = my_profile(user, db)
    applications = (
        db.query(Application).filter(Application.candidate_id == candidate.id).order_by(Application.id.desc()).all()
    )
    return [to_my_application(a) for a in applications]


@router.post("/applications", response_model=MyApplication, status_code=201, summary="Postularme a una vacante")
def apply_to_job(data: ApplyInput, user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    candidate = my_profile(user, db)
    return to_my_application(create_application(db, data.job_id, candidate.id))


@router.delete("/applications/{application_id}", summary="Retirar mi postulación")
def withdraw(application_id: int, user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    candidate = my_profile(user, db)
    application = db.get(Application, application_id)
    # Someone else's application looks the same as a missing one
    if not application or application.candidate_id != candidate.id:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")
    if application.status == "hired":
        raise HTTPException(status_code=409, detail="Una postulación con contratación no se puede retirar")
    db.delete(application)
    db.commit()
    return {"message": "Postulación retirada"}
