from typing import Literal

from pydantic import BaseModel

Area = Literal["technology", "administration", "sales", "soft_skills", "general"]


class SkillToDevelop(BaseModel):
    skill: str
    open_jobs_requiring: int
    suggestion: str


class CandidateInsights(BaseModel):
    candidate_id: int
    name: str
    summary: str
    main_area: Area
    skills_by_area: dict[str, list[str]]
    inferred_skills: dict[str, str]
    skills_to_develop: list[SkillToDevelop]


class InterviewQuestion(BaseModel):
    type: Literal["strength", "inferred", "gap", "experience", "area", "motivation"]
    question: str


class TrainingSuggestion(BaseModel):
    skill: str
    suggestion: str


class InterviewGuide(BaseModel):
    application_id: int
    candidate_name: str
    job_title: str
    score: float
    classification: str
    focus: str
    strengths: list[str]
    gaps: list[str]
    questions: list[InterviewQuestion]
    training_for_gaps: list[TrainingSuggestion]
