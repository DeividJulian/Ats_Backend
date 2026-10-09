from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]

EducationLevel = Literal[
    "high_school", "technician", "technologist", "professional", "specialization", "masters", "doctorate"
]
JobStatusValue = Literal["open", "closed"]


class JobCreate(BaseModel):
    title: Title
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=10000)]
    requirements: Text = ""
    required_skills: list[str] = Field(default_factory=list, max_length=40)
    min_experience_years: int = Field(default=0, ge=0, le=40)
    min_education_level: EducationLevel | None = None


class JobStatus(BaseModel):
    status: JobStatusValue


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    requirements: str
    required_skills: list[str]
    min_experience_years: int
    min_education_level: str | None
    status: str
    created_at: datetime
