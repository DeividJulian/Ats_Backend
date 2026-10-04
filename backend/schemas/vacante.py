from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Titulo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]

NivelEducacion = Literal["bachiller", "tecnico", "tecnologo", "profesional", "especializacion", "maestria", "doctorado"]


class VacanteCreate(BaseModel):
    titulo: Titulo
    descripcion: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=10000)]
    requisitos: Texto = ""
    habilidades_requeridas: list[str] = Field(default_factory=list, max_length=40)
    experiencia_minima_anios: int = Field(default=0, ge=0, le=40)
    nivel_educacion_minimo: NivelEducacion | None = None


class VacanteEstado(BaseModel):
    estado: Literal["abierta", "cerrada"]


class VacanteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str
    requisitos: str
    habilidades_requeridas: list[str]
    experiencia_minima_anios: int
    nivel_educacion_minimo: str | None
    estado: str
    creada_en: datetime
