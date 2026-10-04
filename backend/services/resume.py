"""Reads resumes in PDF format."""
import io

from pypdf import PdfReader
from pypdf.errors import PyPdfError

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
