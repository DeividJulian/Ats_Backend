"""Removes personal data (name, email, phone) from text before it is sent to an external AI provider."""
import re

from services.contact import _EMAIL, _PHONE, extract_name, looks_like_phone

# Each letter also matches its accented forms, so "Sebastian" in the text hides "Sebastián" and vice versa
_ACCENTS = {"a": "aáàä", "e": "eéèë", "i": "iíìï", "o": "oóòö", "u": "uúùü", "n": "nñ"}
_PLAIN = {accented: plain for plain, group in _ACCENTS.items() for accented in group}


def _name_pattern(part: str) -> re.Pattern:
    letters = "".join(f"[{_ACCENTS[_PLAIN.get(c, c)]}]" if _PLAIN.get(c, c) in _ACCENTS else re.escape(c) for c in part.lower())
    return re.compile(rf"(?<!\w){letters}(?!\w)", re.IGNORECASE)


def redact_personal_data(text: str, names: tuple[str | None, ...] = (), emails: tuple[str | None, ...] = (),
                         phones: tuple[str | None, ...] = ()) -> str:
    """Replaces the given (and any detectable) emails, phones and names with neutral placeholders."""
    result = text or ""
    for email in emails:
        if email:
            result = re.sub(re.escape(email), "[correo]", result, flags=re.IGNORECASE)
    result = _EMAIL.sub("[correo]", result)
    for phone in phones:
        if phone:
            result = result.replace(phone, "[teléfono]")

    result = _PHONE.sub(lambda m: "[teléfono]" if looks_like_phone(m.group(0)) else m.group(0), result)
    # Every part of the name (first names and surnames) counts as personal data
    for name in names:
        for part in (name or "").split():
            if len(part) >= 3:
                result = _name_pattern(part).sub("[candidato]", result)
    return result


def redact_resume(text: str) -> str:
    """For a resume not linked to a candidate: hides the name it starts with, plus any email and phone."""
    return redact_personal_data(text, names=(extract_name(text),))
