"""Extracts years of experience and education level from resume text."""
import re

from services.nlp import normalize

LEVELS = {
    "bachiller": 1,
    "tecnico": 2,
    "tecnologo": 3,
    "profesional": 4,
    "especializacion": 5,
    "maestria": 6,
    "doctorado": 7,
}

# From highest to lowest level; the first one found in the text wins
_LEVEL_KEYWORDS = [
    ("doctorado", ["doctorado", "phd"]),
    ("maestria", ["maestria", "magister", "master"]),
    ("especializacion", ["especializacion", "especialista en"]),
    (
        "profesional",
        ["ingenier", "licenciad", "universitari", "pregrado", "contador publico", "administrador de",
         "abogad", "psicolog", "profesional en", "economista"],
    ),
    ("tecnologo", ["tecnologo", "tecnologia en"]),
    ("tecnico", ["tecnico"]),
    ("bachiller", ["bachiller"]),
]

_EXPERIENCE_PATTERNS = [
    re.compile(r"(\d{1,2})\s*\+?\s*(?:anos?|years?)\s+(?:de\s+)?(?:experiencia|exp)"),
    re.compile(r"experiencia\s+(?:laboral\s+)?(?:de\s+|mayor a\s+|superior a\s+)?(?:mas de\s+)?(\d{1,2})\s*\+?\s*(?:anos?|years?)"),
]


def level_to_number(level: str | None) -> int:
    return LEVELS.get(level or "", 0)


def extract_experience_years(text: str | None) -> int:
    """Looks for phrases like '5 años de experiencia' and returns the highest value found."""
    normalized = normalize(text)
    values = [int(m) for pattern in _EXPERIENCE_PATTERNS for m in pattern.findall(normalized)]
    values = [v for v in values if 0 <= v <= 45]
    return max(values) if values else 0


def extract_education_level(text: str | None) -> str | None:
    """Returns the highest education level mentioned, or None if none is detected."""
    normalized = normalize(text)
    for level, keywords in _LEVEL_KEYWORDS:
        if any(k in normalized for k in keywords):
            return level
    return None
