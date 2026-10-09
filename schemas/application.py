from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.nlp import SPANISH_ALIASES

ApplicationStatusValue = Literal["nuevo", "preseleccionado", "entrevista", "oferta", "contratado", "rechazado"]


class ApplicationCreate(BaseModel):
    model_config = SPANISH_ALIASES

    job_id: int = Field(gt=0, alias="vacante_id")
    candidate_id: int = Field(gt=0, alias="candidato_id")


class ApplicationStatus(BaseModel):
    model_config = SPANISH_ALIASES

    status: ApplicationStatusValue = Field(alias="estado")


class ApplicationOut(BaseModel):
    model_config = ConfigDict(**SPANISH_ALIASES, from_attributes=True)

    id: int
    job_id: int = Field(alias="vacante_id")
    candidate_id: int = Field(alias="candidato_id")
    score: float
    details: dict[str, Any] = Field(alias="detalle")
    status: str = Field(alias="estado")
    created_at: datetime = Field(alias="creada_en")


class RankingItem(BaseModel):
    model_config = SPANISH_ALIASES

    position: int = Field(alias="posicion")
    application_id: int = Field(alias="postulacion_id")
    candidate_id: int = Field(alias="candidato_id")
    name: str = Field(alias="nombre")
    email: str
    score: float
    classification: str = Field(alias="clasificacion")
    status: str = Field(alias="estado")
    matching_skills: list[str] = Field(alias="habilidades_coincidentes")
    missing_skills: list[str] = Field(alias="habilidades_faltantes")


class Suggestion(BaseModel):
    model_config = SPANISH_ALIASES

    candidate_id: int = Field(alias="candidato_id")
    name: str = Field(alias="nombre")
    email: str
    score: float
    classification: str = Field(alias="clasificacion")
    matching_skills: list[str] = Field(alias="habilidades_coincidentes")
    missing_skills: list[str] = Field(alias="habilidades_faltantes")
