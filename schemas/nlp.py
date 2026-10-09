from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=20000)]

# Attributes are in English; the aliases are the Spanish field names the API exposes
SPANISH_ALIASES = ConfigDict(validate_by_name=True, validate_by_alias=True, serialize_by_alias=True)


class TextInput(BaseModel):
    model_config = SPANISH_ALIASES

    text: LongText = Field(alias="texto")


class TextAnalysis(BaseModel):
    model_config = SPANISH_ALIASES

    skills: list[str] = Field(alias="habilidades")
    experience_years: int = Field(alias="anios_experiencia")
    education_level: str | None = Field(alias="nivel_educacion")
    key_terms: list[str] = Field(alias="terminos_clave")


class ComparisonInput(BaseModel):
    model_config = SPANISH_ALIASES

    text_a: LongText = Field(alias="texto_a")
    text_b: LongText = Field(alias="texto_b")


class ComparisonOutput(BaseModel):
    model_config = SPANISH_ALIASES

    similarity: float = Field(alias="similitud")
