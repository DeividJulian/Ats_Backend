from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from schemas.ai import AIEvaluation, AIResumeProfile, AIStatus, DraftJobInput, JobDraft
from schemas.nlp import TextInput
from services import ai, llm
from services.matching import candidate_to_dict, job_to_dict

router = APIRouter(prefix="/ai", tags=["IA (Claude)"])


def _run(function, *args):
    """Turns model errors into clear HTTP responses."""
    try:
        return function(*args)
    except llm.LLMNotConfigured:
        raise HTTPException(status_code=503, detail="La IA no está configurada: falta ANTHROPIC_API_KEY en el servidor")
    except llm.LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/status", response_model=AIStatus, summary="Estado de la IA")
def ai_status():
    """Indica si la IA con Claude está configurada y qué modelo usa."""
    return AIStatus(configured=llm.is_configured(), model=llm.model_name())


@router.post("/evaluate/{application_id}", response_model=AIEvaluation, summary="Evaluar postulación con IA")
def evaluate_application(application_id: int, db: Session = Depends(get_db)):
    """Resumen, fortalezas, brechas, recomendación y preguntas de entrevista. No cambia el puntaje del sistema."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")
    result = _run(
        ai.evaluate_candidate,
        job_to_dict(application.job),
        candidate_to_dict(application.candidate),
        application.details or {},
    )
    return AIEvaluation(application_id=application.id, system_score=application.score, **result)


@router.post("/extract-resume", response_model=AIResumeProfile, summary="Extraer perfil de una hoja de vida con IA")
def extract_resume(data: TextInput):
    """Habilidades, años de experiencia, nivel educativo y un resumen a partir del texto de una hoja de vida."""
    return _run(ai.extract_resume_profile, data.text)


@router.post("/draft-job", response_model=JobDraft, summary="Redactar vacante con IA")
def draft_job(data: DraftJobInput):
    """Borrador de una oferta a partir del nombre del cargo y unas notas. No se guarda: sirve para llenar el formulario."""
    return _run(ai.draft_job, data.title, data.notes)
