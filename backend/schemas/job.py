from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from schemas.nlp import SPANISH_ALIASES

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]

EducationLevel = Literal["bachiller", "tecnico", "tecnologo", "profesional", "especializacion", "maestria", "doctorado"]


class JobCreate(BaseModel):
    model_config = SPANISH_ALIASES

    title: Title = Field(alias="titulo")
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=10000)] = Field(
        alias="descripcion"
    )
    requirements: Text = Field(default="", alias="requisitos")
    required_skills: list[str] = Field(default_factory=list, max_length=40, alias="habilidades_requeridas")
    min_experience_years: int = Field(default=0, ge=0, le=40, alias="experiencia_minima_anios")
    min_education_level: EducationLevel | None = Field(default=None, alias="nivel_educacion_minimo")


class JobStatus(BaseModel):
    model_config = SPANISH_ALIASES

    status: Literal["abierta", "cerrada"] = Field(alias="estado")


class JobOut(BaseModel):
    model_config = ConfigDict(**SPANISH_ALIASES, from_attributes=True)

    id: int
    title: str = Field(alias="titulo")
    description: str = Field(alias="descripcion")
    requirements: str = Field(alias="requisitos")
    required_skills: list[str] = Field(alias="habilidades_requeridas")
    min_experience_years: int = Field(alias="experiencia_minima_anios")
    min_education_level: str | None = Field(alias="nivel_educacion_minimo")
    status: str = Field(alias="estado")
    created_at: datetime = Field(alias="creada_en")
