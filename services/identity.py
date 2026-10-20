"""Checks that a resume belongs to the person whose profile receives it.

Uses the system's own NLP (name and email detection), never the external AI: the name and the email
are exactly the data we promised not to send to the language model.
"""
import re

from fastapi import HTTPException

from services.contact import _EMAIL, extract_name
from services.nlp import normalize

# Words that are part of many Spanish names and say nothing about who the person is
_CONNECTORS = {"de", "del", "la", "las", "los", "y", "da", "van", "von"}
# The name is usually at the top; looking further down would catch references and former bosses
_HEAD_CHARS = 800


def name_words(name: str | None) -> set[str]:
    """Distinctive words of a name, without accents or case: "José de la Peña" → {"jose", "pena"}."""
    return {w for w in re.findall(r"[a-z]+", normalize(name or "")) if len(w) > 1 and w not in _CONNECTORS}


def same_person(a: str | None, b: str | None) -> bool:
    """Two names match when they share at least two words (first name and a surname),
    or the only word of a one-word name."""
    wa, wb = name_words(a), name_words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) >= min(2, len(wa), len(wb))


def resume_mismatch(person_name: str, person_email: str | None, text: str) -> str | None:
    """Returns why the resume seems to be someone else's, or None when it is theirs (or nothing says otherwise)."""
    if not (text or "").strip():
        return None
    emails = {e.lower() for e in _EMAIL.findall(text)}
    if person_email and person_email.lower() in emails:
        return None

    detected = extract_name(text)
    if detected:
        if same_person(person_name, detected):
            return None
        return f"La hoja de vida es de «{detected}», pero el perfil es de «{person_name}»"

    # No clear name line: is the person's name written near the top?
    head = name_words(text[:_HEAD_CHARS])
    words = name_words(person_name)
    if words and len(words & head) >= min(2, len(words)):
        return None
    if emails:
        return f"La hoja de vida tiene el correo {sorted(emails)[0]}, que no es el de «{person_name}»"
    # Nothing identifies anybody: it can't be proven to be someone else's
    return None


def reject_if_not_theirs(person_name: str, person_email: str | None, text: str, own: bool = False) -> None:
    """422 when the resume belongs to someone else; nothing is saved."""
    reason = resume_mismatch(person_name, person_email, text)
    if reason:
        advice = "Sube tu propia hoja de vida." if own else "Revisa que sea la hoja de vida del candidato correcto."
        raise HTTPException(status_code=422, detail=f"{reason}. {advice}")
