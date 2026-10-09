from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models.candidate import Candidate
from schemas.candidate import CandidateOut
from services.profile import extract_education_level, extract_experience_years
from services.resume import InvalidResumeError, extract_pdf_text
from services.skills import extract_skills

router = APIRouter(prefix="/candidates", tags=["Hojas de vida"])


@router.post("/{candidate_id}/resume", response_model=CandidateOut, summary="Subir hoja de vida en PDF")
async def upload_resume(candidate_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Recibe un PDF, extrae su texto y actualiza el perfil del candidato con lo que detecte."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    content = await file.read()
    try:
        text = extract_pdf_text(content)
    except InvalidResumeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    candidate.resume_text = text[:20000]
    candidate.skills = sorted(set(candidate.skills or []) | set(extract_skills(text)))
    candidate.experience_years = max(candidate.experience_years or 0, extract_experience_years(text))
    candidate.education_level = candidate.education_level or extract_education_level(text)
    db.commit()
    db.refresh(candidate)
    return candidate
