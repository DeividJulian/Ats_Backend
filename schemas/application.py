from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatusValue = Literal["new", "shortlisted", "interview", "offer", "hired", "rejected"]


class ApplicationCreate(BaseModel):
    job_id: int = Field(gt=0)
    candidate_id: int = Field(gt=0)


class ApplicationStatus(BaseModel):
    status: ApplicationStatusValue


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    candidate_id: int
    score: float
    details: dict[str, Any]
    status: str
    created_at: datetime


class RankingItem(BaseModel):
    position: int
    application_id: int
    candidate_id: int
    name: str
    email: str
    score: float
    classification: str
    status: str
    matching_skills: list[str]
    missing_skills: list[str]


class Suggestion(BaseModel):
    candidate_id: int
    name: str
    email: str
    score: float
    classification: str
    matching_skills: list[str]
    missing_skills: list[str]


class JobRecommendation(BaseModel):
    job_id: int
    title: str
    score: float
    classification: str
    matching_skills: list[str]
    missing_skills: list[str]
