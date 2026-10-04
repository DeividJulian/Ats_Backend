from collections import Counter

from fastapi import APIRouter

from schemas.nlp import AnalisisTexto, TextoEntrada
from services.habilidades import extraer_habilidades
from services.nlp import tokenizar
from services.perfil import extraer_anios_experiencia, extraer_nivel_educacion

router = APIRouter(prefix="/nlp", tags=["NLP"])


@router.post("/analizar-texto", response_model=AnalisisTexto)
def analizar_texto(entrada: TextoEntrada):
    """Extrae habilidades, experiencia y nivel educativo de cualquier texto (hoja de vida o vacante)."""
    frecuencias = Counter(tokenizar(entrada.texto))
    return AnalisisTexto(
        habilidades=extraer_habilidades(entrada.texto),
        anios_experiencia=extraer_anios_experiencia(entrada.texto),
        nivel_educacion=extraer_nivel_educacion(entrada.texto),
        terminos_clave=[t for t, _ in frecuencias.most_common(8)],
    )
