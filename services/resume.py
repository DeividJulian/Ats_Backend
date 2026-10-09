"""Reads resumes in PDF format."""
import io
from collections import Counter

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from services.contact import extract_email, extract_name, extract_phone
from services.nlp import tokenize
from services.profile import extract_education_level, extract_experience_years
from services.skills import extract_skills

MAX_BYTES = 5 * 1024 * 1024


class InvalidResumeError(Exception):
    pass


def extract_pdf_text(content: bytes) -> str:
    # Error messages are shown to the client, so they stay in Spanish
    if len(content) > MAX_BYTES:
        raise InvalidResumeError("El archivo supera el máximo de 5 MB")
    if not content.startswith(b"%PDF"):
        raise InvalidResumeError("El archivo no es un PDF válido")
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [(p.extract_text() or "") for p in reader.pages[:15]]
    except (PyPdfError, ValueError, KeyError) as e:
        raise InvalidResumeError("No se pudo leer el PDF") from e
    text = "\n".join(pages).strip()
    if len(text) < 20:
        raise InvalidResumeError("No se pudo extraer texto del PDF (¿es una imagen escaneada?)")
    return text


def analyze_resume_text(text: str) -> dict:
    """Everything the system can detect in a resume: contact data and professional profile."""
    email = extract_email(text)
    return {
        "name": extract_name(text, email),
        "email": email,
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "experience_years": extract_experience_years(text),
        "education_level": extract_education_level(text),
        "key_terms": [t for t, _ in Counter(tokenize(text)).most_common(8)],
    }
