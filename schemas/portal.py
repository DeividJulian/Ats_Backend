from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from schemas.candidate import Name
from schemas.job import EducationLevel


class ProfileUpdate(BaseModel):
    """What candidates can edit about themselves (the email is their login and stays fixed)."""

    name: Name
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    resume_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20000)] = ""
    skills: list[str] = Field(default_factory=list, max_length=60)
    experience_years: int | None = Field(default=None, ge=0, le=45)
    education_level: EducationLevel | None = None


class ApplyInput(BaseModel):
    job_id: int = Field(gt=0)


class MyApplication(BaseModel):
    """A candidate's own application. The numeric score is for recruiters, so it is not included."""

    id: int
    job_id: int
    job_title: str
    job_status: str
    status: str
    matching_skills: list[str]
    missing_skills: list[str]
    created_at: datetime


class PublicJob(BaseModel):
    id: int
    title: str
    description: str
    requirements: str
    required_skills: list[str]
    min_experience_years: int
    min_education_level: str | None
    created_at: datetime


class PublicSummary(BaseModel):
    open_jobs: int
    candidates: int
    hires: int
