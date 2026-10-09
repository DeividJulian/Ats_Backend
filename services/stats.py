"""Hiring process statistics: funnel, scores per job and talent gaps."""
from collections import Counter

from sqlalchemy.orm import Session

from models.application import Application
from models.candidate import Candidate
from models.job import Job
from services.pipeline import TRANSITIONS


def compute_statistics(db: Session) -> dict:
    jobs = db.query(Job).all()
    candidates = db.query(Candidate).all()
    applications = db.query(Application).all()

    funnel = {status: 0 for status in TRANSITIONS}
    for a in applications:
        funnel[a.status] = funnel.get(a.status, 0) + 1

    scores_by_job = {}
    for a in applications:
        scores_by_job.setdefault(a.job_id, []).append(a.score)

    # The returned keys are shown to the client, so they stay in Spanish
    per_job = [
        {
            "vacante_id": j.id,
            "titulo": j.title,
            "estado": j.status,
            "postulaciones": len(scores_by_job.get(j.id, [])),
            "score_promedio": round(sum(scores_by_job[j.id]) / len(scores_by_job[j.id]), 1)
            if scores_by_job.get(j.id)
            else 0.0,
            "score_maximo": max(scores_by_job.get(j.id, [0.0])),
        }
        for j in jobs
    ]

    demanded = Counter(s for j in jobs for s in (j.required_skills or []))
    available = Counter(s for c in candidates for s in (c.skills or []))
    most_demanded = [
        {"habilidad": s, "vacantes": n, "candidatos_que_la_tienen": available.get(s, 0)}
        for s, n in demanded.most_common(10)
    ]
    # Gap: required skills that almost no candidate has
    gaps = sorted(
        (x for x in most_demanded if x["candidatos_que_la_tienen"] < x["vacantes"] * 2),
        key=lambda x: x["candidatos_que_la_tienen"],
    )

    hired = funnel.get("contratado", 0)
    return {
        "totales": {
            "vacantes": len(jobs),
            "vacantes_abiertas": sum(1 for j in jobs if j.status == "abierta"),
            "candidatos": len(candidates),
            "postulaciones": len(applications),
        },
        "embudo": funnel,
        "tasa_contratacion_pct": round(100 * hired / len(applications), 1) if applications else 0.0,
        "por_vacante": per_job,
        "habilidades_mas_demandadas": most_demanded,
        "brechas_de_talento": gaps,
    }
