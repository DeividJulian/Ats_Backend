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

    per_job = [
        {
            "job_id": j.id,
            "title": j.title,
            "status": j.status,
            "applications": len(scores_by_job.get(j.id, [])),
            "average_score": round(sum(scores_by_job[j.id]) / len(scores_by_job[j.id]), 1)
            if scores_by_job.get(j.id)
            else 0.0,
            "max_score": max(scores_by_job.get(j.id, [0.0])),
        }
        for j in jobs
    ]

    demanded = Counter(s for j in jobs for s in (j.required_skills or []))
    available = Counter(s for c in candidates for s in (c.skills or []))
    most_demanded = [
        {"skill": s, "jobs": n, "candidates_with_skill": available.get(s, 0)}
        for s, n in demanded.most_common(10)
    ]
    # Gap: required skills that almost no candidate has
    gaps = sorted(
        (x for x in most_demanded if x["candidates_with_skill"] < x["jobs"] * 2),
        key=lambda x: x["candidates_with_skill"],
    )

    hired = funnel.get("hired", 0)
    return {
        "totals": {
            "jobs": len(jobs),
            "open_jobs": sum(1 for j in jobs if j.status == "open"),
            "candidates": len(candidates),
            "applications": len(applications),
        },
        "funnel": funnel,
        "hire_rate_pct": round(100 * hired / len(applications), 1) if applications else 0.0,
        "per_job": per_job,
        "most_demanded_skills": most_demanded,
        "talent_gaps": gaps,
    }
