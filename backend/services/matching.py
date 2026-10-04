"""Connects the database with the match computation: builds the input data and the TF-IDF corpus."""
from sqlalchemy.orm import Session

from models.candidate import Candidate
from models.job import Job
from services.scoring import compute_match


def job_to_dict(job: Job) -> dict:
    return {
        "title": job.title,
        "description": job.description,
        "requirements": job.requirements,
        "required_skills": job.required_skills or [],
        "min_experience_years": job.min_experience_years,
        "min_education_level": job.min_education_level,
    }


def candidate_to_dict(candidate: Candidate) -> dict:
    return {
        "resume_text": candidate.resume_text,
        "skills": candidate.skills or [],
        "experience_years": candidate.experience_years,
        "education_level": candidate.education_level,
    }


def system_corpus(db: Session) -> list[str]:
    """Every known text: makes common terms weigh less and distinctive ones weigh more."""
    texts = [f"{j.title} {j.description} {j.requirements}" for j in db.query(Job).all()]
    texts += [c.resume_text for c in db.query(Candidate).all() if c.resume_text]
    return texts


def evaluate(db: Session, job: Job, candidate: Candidate, corpus: list[str] | None = None) -> dict:
    if corpus is None:
        corpus = system_corpus(db)
    return compute_match(job_to_dict(job), candidate_to_dict(candidate), corpus)
