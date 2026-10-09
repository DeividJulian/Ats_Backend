from collections import Counter

from fastapi import APIRouter

from schemas.nlp import ComparisonInput, ComparisonOutput, TextAnalysis, TextInput
from services.nlp import tokenize
from services.profile import extract_education_level, extract_experience_years
from services.similarity import cosine_similarity
from services.skills import extract_skills

router = APIRouter(prefix="/nlp", tags=["NLP"])


@router.post("/analyze-text", response_model=TextAnalysis, summary="Analizar texto")
def analyze_text(data: TextInput):
    """Extrae habilidades, experiencia y nivel educativo de cualquier texto (hoja de vida o vacante)."""
    frequencies = Counter(tokenize(data.text))
    return TextAnalysis(
        skills=extract_skills(data.text),
        experience_years=extract_experience_years(data.text),
        education_level=extract_education_level(data.text),
        key_terms=[t for t, _ in frequencies.most_common(8)],
    )


@router.post("/similarity", response_model=ComparisonOutput, summary="Comparar textos")
def compare_texts(data: ComparisonInput):
    """Similitud semántica léxica (TF-IDF + coseno) entre dos textos, de 0 a 1."""
    return ComparisonOutput(similarity=cosine_similarity(data.text_a, data.text_b))
