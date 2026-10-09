from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.candidate import Candidate
from models.job import Job
from schemas.application import ApplicationOut, JobRecommendation, RankingItem, Suggestion
from services.matching import evaluate, system_corpus

router = APIRouter(tags=["Ranking"])


def _job_or_404(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return job


@router.get("/jobs/{job_id}/ranking", response_model=list[RankingItem], summary="Ranking de la vacante")
def job_ranking(job_id: int, db: Session = Depends(get_db)):
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
            classification=a.details.get("classification", "low"),
            status=a.status,
            matching_skills=a.details.get("matching_skills", []),
            missing_skills=a.details.get("missing_skills", []),
        )
        for i, a in enumerate(applications, start=1)
    ]


@router.post(
    "/applications/{application_id}/recalculate", response_model=ApplicationOut, summary="Recalcular postulación"
)
def recalculate_application(application_id: int, db: Session = Depends(get_db)):
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


@router.post("/jobs/{job_id}/recalculate-ranking", summary="Recalcular ranking de la vacante")
def recalculate_ranking(job_id: int, db: Session = Depends(get_db)):
    """Vuelve a calcular el score de todas las postulaciones de la vacante."""
    job = _job_or_404(db, job_id)
    corpus = system_corpus(db)
    applications = db.query(Application).filter(Application.job_id == job_id).all()
    for a in applications:
        result = evaluate(db, job, a.candidate, corpus)
        a.score = result["score"]
        a.details = result
    db.commit()
    return {"message": "Ranking recalculado", "updated_applications": len(applications)}


@router.get(
    "/jobs/{job_id}/suggested-candidates", response_model=list[Suggestion], summary="Candidatos sugeridos"
)
def suggested_candidates(
    job_id: int,
    limit: int = Query(default=5, ge=1, le=50),
    min_score: float = Query(default=0, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """Recomienda candidatos de la base que todavía NO se han postulado, ordenados por ajuste."""
    job = _job_or_404(db, job_id)
    already_applied = {a.candidate_id for a in db.query(Application).filter(Application.job_id == job_id)}
    corpus = system_corpus(db)

    suggestions = []
    for candidate in db.query(Candidate).all():
        if candidate.id in already_applied:
            continue
        r = evaluate(db, job, candidate, corpus)
        if r["score"] >= min_score:
            suggestions.append(
                Suggestion(
                    candidate_id=candidate.id,
                    name=candidate.name,
                    email=candidate.email,
                    score=r["score"],
                    classification=r["classification"],
                    matching_skills=r["matching_skills"],
                    missing_skills=r["missing_skills"],
                )
            )
    suggestions.sort(key=lambda s: s.score, reverse=True)
    return suggestions[:limit]


@router.get(
    "/candidates/{candidate_id}/recommended-jobs",
    response_model=list[JobRecommendation],
    summary="Vacantes recomendadas para un candidato",
)
def recommended_jobs(
    candidate_id: int,
    limit: int = Query(default=5, ge=1, le=50),
    min_score: float = Query(default=0, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """Vacantes abiertas a las que el candidato todavía NO se ha postulado, ordenadas por ajuste."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    applied = {a.job_id for a in db.query(Application).filter(Application.candidate_id == candidate_id)}
    corpus = system_corpus(db)

    recommendations = []
    for job in db.query(Job).filter(Job.status == "open").all():
        if job.id in applied:
            continue
        r = evaluate(db, job, candidate, corpus)
        if r["score"] >= min_score:
            recommendations.append(
                JobRecommendation(
                    job_id=job.id,
                    title=job.title,
                    score=r["score"],
                    classification=r["classification"],
                    matching_skills=r["matching_skills"],
                    missing_skills=r["missing_skills"],
                )
            )
    recommendations.sort(key=lambda j: j.score, reverse=True)
    return recommendations[:limit]
