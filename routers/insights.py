from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.candidate import Candidate
from models.job import Job
from schemas.insights import CandidateInsights, InterviewGuide
from services.insights import candidate_insights, interview_guide

router = APIRouter(tags=["IA"])


@router.get("/candidates/{candidate_id}/insights", response_model=CandidateInsights, summary="Análisis del candidato")
def get_candidate_insights(candidate_id: int, db: Session = Depends(get_db)):
    """Resumen del perfil, área principal, habilidades inferidas y qué le conviene aprender según las vacantes abiertas."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    open_jobs = db.query(Job).filter(Job.status == "open").all()
    insights = candidate_insights(
        candidate.skills or [],
        candidate.experience_years or 0,
        candidate.education_level,
        [j.required_skills or [] for j in open_jobs],
    )
    return CandidateInsights(candidate_id=candidate.id, name=candidate.name, **insights)


@router.get(
    "/applications/{application_id}/interview-guide", response_model=InterviewGuide, summary="Guía de entrevista"
)
def get_interview_guide(application_id: int, db: Session = Depends(get_db)):
    """Preguntas de entrevista personalizadas según las fortalezas y brechas del candidato frente a la vacante."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")
    job, candidate = application.job, application.candidate
    guide = interview_guide(
        job.title,
        job.required_skills or [],
        job.min_experience_years or 0,
        application.details or {},
        candidate.experience_years or 0,
    )
    return InterviewGuide(
        application_id=application.id,
        candidate_name=candidate.name,
        job_title=job.title,
        score=application.score,
        classification=(application.details or {}).get("classification", "low"),
        **guide,
    )
