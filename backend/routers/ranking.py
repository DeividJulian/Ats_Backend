from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.job import Job
from schemas.application import ApplicationOut, RankingItem
from services.matching import evaluate, system_corpus

router = APIRouter(tags=["Ranking"])

JobId = Path(alias="vacante_id")
ApplicationId = Path(alias="postulacion_id")


def _job_or_404(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return job


@router.get("/vacantes/{vacante_id}/ranking", response_model=list[RankingItem], summary="Ranking de la vacante")
def job_ranking(job_id: int = JobId, db: Session = Depends(get_db)):
    """Candidatos postulados, del mejor al peor ajuste."""
    _job_or_404(db, job_id)
    applications = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.score.desc(), Application.id)
        .all()
    )
    return [
        RankingItem(
            position=i,
            application_id=a.id,
            candidate_id=a.candidate_id,
            name=a.candidate.name,
            email=a.candidate.email,
            score=a.score,
            classification=a.details.get("clasificacion", "bajo"),
            status=a.status,
            matching_skills=a.details.get("habilidades_coincidentes", []),
            missing_skills=a.details.get("habilidades_faltantes", []),
        )
        for i, a in enumerate(applications, start=1)
    ]


@router.post(
    "/postulaciones/{postulacion_id}/recalcular", response_model=ApplicationOut, summary="Recalcular postulación"
)
def recalculate_application(application_id: int = ApplicationId, db: Session = Depends(get_db)):
    """Vuelve a calcular el score (útil si se editó la vacante o la hoja de vida del candidato)."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")
    result = evaluate(db, application.job, application.candidate)
    application.score = result["score"]
    application.details = result
    db.commit()
    db.refresh(application)
    return application


@router.post("/vacantes/{vacante_id}/recalcular-ranking", summary="Recalcular ranking de la vacante")
def recalculate_ranking(job_id: int = JobId, db: Session = Depends(get_db)):
    """Vuelve a calcular el score de todas las postulaciones de la vacante."""
    job = _job_or_404(db, job_id)
    corpus = system_corpus(db)
    applications = db.query(Application).filter(Application.job_id == job_id).all()
    for a in applications:
        result = evaluate(db, job, a.candidate, corpus)
        a.score = result["score"]
        a.details = result
    db.commit()
    return {"mensaje": "Ranking recalculado", "postulaciones_actualizadas": len(applications)}
