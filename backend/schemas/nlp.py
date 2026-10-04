from typing import Annotated

from pydantic import BaseModel, StringConstraints

TextoLargo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=20000)]


class TextoEntrada(BaseModel):
    texto: TextoLargo


class AnalisisTexto(BaseModel):
    habilidades: list[str]
    anios_experiencia: int
    nivel_educacion: str | None
    terminos_clave: list[str]
