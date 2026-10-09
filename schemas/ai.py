from typing import Annotated

from pydantic import BaseModel, StringConstraints

from services.ai import EducationLevel, Recommendation


class AIStatus(BaseModel):
    configured: bool
    model: str


class AIEvaluation(BaseModel):
    application_id: int
    system_score: float
    summary: str
    strengths: list[str]
    gaps: list[str]
    recommendation: Recommendation
    interview_questions: list[str]


class AIResumeProfile(BaseModel):
    skills: list[str]
    experience_years: int
    education_level: EducationLevel | None
    summary: str


class DraftJobInput(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""


class JobDraft(BaseModel):
    description: str
    requirements: str
    required_skills: list[str]
    min_experience_years: int
    min_education_level: EducationLevel | None
