from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from schemas.job import EducationLevel
from schemas.nlp import SPANISH_ALIASES

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


class CandidateCreate(BaseModel):
    model_config = SPANISH_ALIASES

    name: Name = Field(alias="nombre")
    email: EmailStr
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = Field(
        default=None, alias="telefono"
    )
    resume_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20000)] = Field(
        default="", alias="cv_texto"
    )
    # Optional: when not sent, they are extracted automatically from the resume text
    skills: list[str] = Field(default_factory=list, max_length=60, alias="habilidades")
    experience_years: int | None = Field(default=None, ge=0, le=45, alias="anios_experiencia")
    education_level: EducationLevel | None = Field(default=None, alias="nivel_educacion")


class CandidateOut(BaseModel):
    model_config = ConfigDict(**SPANISH_ALIASES, from_attributes=True)

    id: int
    name: str = Field(alias="nombre")
    email: str
    phone: str | None = Field(alias="telefono")
    resume_text: str = Field(alias="cv_texto")
    skills: list[str] = Field(alias="habilidades")
    experience_years: int = Field(alias="anios_experiencia")
    education_level: str | None = Field(alias="nivel_educacion")
    created_at: datetime = Field(alias="creado_en")
