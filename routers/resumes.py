from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.candidate import Candidate
from schemas.candidate import CandidateOut
from schemas.nlp import ResumeAnalysis
from services.profile import extract_education_level, extract_experience_years
from services.resume import InvalidResumeError, analyze_resume_text, extract_pdf_text
from services.skills import extract_skills, sort_skills

router = APIRouter(tags=["Hojas de vida"])


async def read_pdf_or_422(file: UploadFile) -> str:
    try:
        return extract_pdf_text(await file.read())
    except InvalidResumeError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/nlp/analyze-resume", response_model=ResumeAnalysis, summary="Analizar hoja de vida en PDF")
async def analyze_resume(file: UploadFile = File(...)):
    """Detecta datos de contacto y perfil profesional de un PDF sin guardar nada (vista previa)."""
    return analyze_resume_text(await read_pdf_or_422(file))


@router.post(
    "/candidates/from-resume", response_model=CandidateOut, status_code=201, summary="Crear candidato desde un PDF"
)
async def create_candidate_from_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Lee la hoja de vida y crea el candidato con el nombre, correo, teléfono y perfil que detecte."""
    text = await read_pdf_or_422(file)
    data = analyze_resume_text(text)
    if not data["email"]:
        raise HTTPException(status_code=422, detail="No se encontró un correo electrónico en la hoja de vida")
    if not data["name"]:
        raise HTTPException(status_code=422, detail="No se pudo identificar el nombre del candidato en la hoja de vida")
    if db.query(Candidate).filter(func.lower(Candidate.email) == data["email"]).first():
        raise HTTPException(status_code=409, detail="Ya existe un candidato con ese correo")

    candidate = Candidate(
        name=data["name"][:100],
        email=data["email"],
        phone=data["phone"],
        resume_text=text[:20000],
        skills=data["skills"],
        experience_years=data["experience_years"],
        education_level=data["education_level"],
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/candidates/{candidate_id}/resume", response_model=CandidateOut, summary="Subir hoja de vida en PDF")
async def upload_resume(candidate_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Recibe un PDF, extrae su texto y actualiza el perfil del candidato con lo que detecte."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    text = await read_pdf_or_422(file)
    candidate.resume_text = text[:20000]
    candidate.skills = sort_skills((candidate.skills or []) + extract_skills(text))
    candidate.experience_years = max(candidate.experience_years or 0, extract_experience_years(text))
    candidate.education_level = candidate.education_level or extract_education_level(text)
    db.commit()
    db.refresh(candidate)
    return candidate
