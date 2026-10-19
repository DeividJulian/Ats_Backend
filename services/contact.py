"""Extracts contact data (name, email, phone) from resume text."""
import re

from services.nlp import normalize

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Optional country code, then 7 to 10 digits that may be grouped with spaces, dots, dashes or parentheses
_PHONE = re.compile(r"(?<![\w@.])(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{1,3}\)?[\s.-]?)?\d{3}[\s.-]?\d{2,4}[\s.-]?\d{2,4}(?![\w@])")

# Lines that look like a heading rather than a person's name
_NOT_A_NAME = {
    "hoja", "vida", "curriculum", "vitae", "cv", "perfil", "profesional", "datos", "personales", "contacto",
    "experiencia", "educacion", "formacion", "habilidades", "resumen", "objetivo", "ingeniero", "ingeniera",
}
_NAME_WORD = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+$")


def extract_email(text: str | None) -> str | None:
    match = _EMAIL.search(text or "")
    return match.group(0).lower() if match else None


_YEAR_RANGE = re.compile(r"(?:19|20)\d{2}\s*[-–/]\s*(?:19|20)\d{2}")


def looks_like_phone(candidate: str) -> bool:
    """7 to 13 digits, and not a range of years such as 2019-2024."""
    digits = re.sub(r"\D", "", candidate)
    core = re.sub(r"^\D+|\D+$", "", candidate)
    return 7 <= len(digits) <= 13 and not _YEAR_RANGE.fullmatch(core)


def extract_phone(text: str | None) -> str | None:
    for match in _PHONE.finditer(text or ""):
        if looks_like_phone(match.group(0)):
            return re.sub(r"\s+", " ", match.group(0).strip())
    return None


def _name_from_email(email: str) -> str | None:
    parts = [p for p in re.split(r"[._-]+", re.sub(r"\d", "", email.split("@")[0])) if len(p) > 1]
    return " ".join(p.capitalize() for p in parts) if len(parts) >= 2 else None


def extract_name(text: str | None, email: str | None = None) -> str | None:
    """The name is usually one of the first lines: 2 to 5 words, letters only, and not a heading."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for line in lines[:6]:
        words = line.split()
        if not 2 <= len(words) <= 5 or not all(_NAME_WORD.match(w) for w in words):
            continue
        if {normalize(w) for w in words} & _NOT_A_NAME:
            continue
        return " ".join(w.capitalize() if w.isupper() or w.islower() else w for w in words)
    return _name_from_email(email) if email else None
