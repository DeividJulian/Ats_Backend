
from fastapi import APIRouter, Depends

from schemas.nlp import ComparisonInput, ComparisonOutput, TextAnalysis, TextInput
from services.auth import staff_only
from services.resume import analyze_resume_text
from services.similarity import cosine_similarity

router = APIRouter(prefix="/nlp", tags=["NLP"], dependencies=[Depends(staff_only)])


@router.post("/analyze-text", response_model=TextAnalysis, summary="Analizar texto")
def analyze_text(data: TextInput):
    """Extrae datos de contacto, habilidades, experiencia y nivel educativo de un texto (hoja de vida o vacante)."""
    return TextAnalysis(**analyze_resume_text(data.text))


@router.post("/similarity", response_model=ComparisonOutput, summary="Comparar textos")
def compare_texts(data: ComparisonInput):
    """Similitud semántica léxica (TF-IDF + coseno) entre dos textos, de 0 a 1."""
    return ComparisonOutput(similarity=cosine_similarity(data.text_a, data.text_b))
