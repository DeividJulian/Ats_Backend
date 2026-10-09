from typing import Annotated

from pydantic import BaseModel, StringConstraints

LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=20000)]


class TextInput(BaseModel):
    text: LongText


class TextAnalysis(BaseModel):
    skills: list[str]
    experience_years: int
    education_level: str | None
    key_terms: list[str]


class ComparisonInput(BaseModel):
    text_a: LongText
    text_b: LongText


class ComparisonOutput(BaseModel):
    similarity: float
