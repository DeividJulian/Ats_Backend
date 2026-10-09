from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from schemas.job import EducationLevel

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


class CandidateCreate(BaseModel):
    name: Name
    email: EmailStr
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    resume_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20000)] = ""
    # Optional: when not sent, they are extracted automatically from the resume text
    skills: list[str] = Field(default_factory=list, max_length=60)
    experience_years: int | None = Field(default=None, ge=0, le=45)
    education_level: EducationLevel | None = None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str | None
    resume_text: str
    skills: list[str]
    experience_years: int
    education_level: str | None
    created_at: datetime
