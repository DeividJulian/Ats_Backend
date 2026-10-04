from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from schemas.vacante import NivelEducacion

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


class CandidatoCreate(BaseModel):
    nombre: Nombre
    email: EmailStr
    telefono: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    cv_texto: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20000)] = ""
    # Opcionales: si no se envían, se extraen automáticamente del texto de la hoja de vida
    habilidades: list[str] = Field(default_factory=list, max_length=60)
    anios_experiencia: int | None = Field(default=None, ge=0, le=45)
    nivel_educacion: NivelEducacion | None = None


class CandidatoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    telefono: str | None
    cv_texto: str
    habilidades: list[str]
    anios_experiencia: int
    nivel_educacion: str | None
    creado_en: datetime
