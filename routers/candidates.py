from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.candidate import Candidate
from schemas.candidate import CandidateCreate, CandidateOut
from services.profile import extract_education_level, extract_experience_years
from services.skills import canonicalize_skills, extract_skills, sort_skills

router = APIRouter(prefix="/candidates", tags=["Candidatos"])


def fill_profile(candidate: Candidate, data: CandidateCreate) -> None:
    """Combines what the recruiter typed with what the system detects in the resume."""
    candidate.name = data.name
    candidate.email = data.email
    candidate.phone = data.phone
    candidate.resume_text = data.resume_text
    candidate.skills = sort_skills(canonicalize_skills(data.skills) + extract_skills(data.resume_text))
    candidate.experience_years = (
        data.experience_years if data.experience_years is not None else extract_experience_years(data.resume_text)
    )
    candidate.education_level = data.education_level or extract_education_level(data.resume_text)


def email_in_use(db: Session, email: str, exclude_id: int | None = None) -> bool:
    query = db.query(Candidate).filter(func.lower(Candidate.email) == email.lower())
    if exclude_id is not None:
        query = query.filter(Candidate.id != exclude_id)
    return query.first() is not None


def get_candidate_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    return candidate


@router.post("", response_model=CandidateOut, status_code=201, summary="Crear candidato")
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)):
    """Las habilidades, la experiencia y el nivel educativo que no se envíen se extraen de la hoja de vida."""
    if email_in_use(db, data.email):
        raise HTTPException(status_code=409, detail="Ya existe un candidato con ese correo")
    candidate = Candidate()
    fill_profile(candidate, data)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("", response_model=list[CandidateOut], summary="Listar candidatos")
def list_candidates(skill: str | None = None, db: Session = Depends(get_db)):
    candidates = db.query(Candidate).order_by(Candidate.id).all()
    if skill:
        wanted = canonicalize_skills([skill])
        if wanted:
            candidates = [c for c in candidates if wanted[0] in (c.skills or [])]
    return candidates


@router.get("/{candidate_id}", response_model=CandidateOut, summary="Obtener candidato")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    return get_candidate_or_404(db, candidate_id)


@router.put("/{candidate_id}", response_model=CandidateOut, summary="Actualizar candidato")
def update_candidate(candidate_id: int, data: CandidateCreate, db: Session = Depends(get_db)):
    candidate = get_candidate_or_404(db, candidate_id)
    if email_in_use(db, data.email, exclude_id=candidate_id):
        raise HTTPException(status_code=409, detail="Ya existe otro candidato con ese correo")
    fill_profile(candidate, data)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", summary="Eliminar candidato")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = get_candidate_or_404(db, candidate_id)
    deleted = db.query(Application).filter(Application.candidate_id == candidate_id).delete()
    db.delete(candidate)
    db.commit()
    return {"message": "Candidato eliminado", "deleted_applications": deleted}
