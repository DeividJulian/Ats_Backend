"""Extracción de años de experiencia y nivel educativo desde el texto de una hoja de vida."""
import re

from services.nlp import normalizar

NIVELES = {
    "bachiller": 1,
    "tecnico": 2,
    "tecnologo": 3,
    "profesional": 4,
    "especializacion": 5,
    "maestria": 6,
    "doctorado": 7,
}

# Del nivel más alto al más bajo; gana el primero que aparezca en el texto
_PALABRAS_NIVEL = [
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

_EXPERIENCIA = [
    re.compile(r"(\d{1,2})\s*\+?\s*(?:anos?|years?)\s+(?:de\s+)?(?:experiencia|exp)"),
    re.compile(r"experiencia\s+(?:laboral\s+)?(?:de\s+|mayor a\s+|superior a\s+)?(?:mas de\s+)?(\d{1,2})\s*\+?\s*(?:anos?|years?)"),
]


def nivel_a_numero(nivel: str | None) -> int:
    return NIVELES.get(nivel or "", 0)


def extraer_anios_experiencia(texto: str | None) -> int:
    """Busca frases como '5 años de experiencia' y devuelve el mayor valor encontrado."""
    normal = normalizar(texto)
    valores = [int(m) for patron in _EXPERIENCIA for m in patron.findall(normal)]
    valores = [v for v in valores if 0 <= v <= 45]
    return max(valores) if valores else 0


def extraer_nivel_educacion(texto: str | None) -> str | None:
    """Devuelve el nivel educativo más alto mencionado, o None si no se detecta."""
    normal = normalizar(texto)
    for nivel, palabras in _PALABRAS_NIVEL:
        if any(p in normal for p in palabras):
            return nivel
    return None
