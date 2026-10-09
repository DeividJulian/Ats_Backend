"""Thin wrapper around the Claude API (official Anthropic SDK) with structured, schema-validated outputs.

Environment variables:
  ANTHROPIC_API_KEY  API key (required to use the AI features)
  ANTHROPIC_MODEL    optional model override
"""
import os
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

DEFAULT_MODEL = "claude-opus-5-5"
TIMEOUT_SECONDS = 60
# If a safety classifier declines a request, the API re-runs it on a recommended fallback model
FALLBACK_BETA = "server-side-fallback-2026-07-01"

T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None


class LLMNotConfigured(Exception):
    """ANTHROPIC_API_KEY is not set."""


class LLMError(Exception):
    """The API failed or returned an unusable answer. The message is shown to the user, so it is in Spanish."""


def model_name() -> str:
    return os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL


def is_configured() -> bool:
    return bool((os.getenv("ANTHROPIC_API_KEY") or "").strip())


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=TIMEOUT_SECONDS)
    return _client


def generate(system: str, user: str, output_type: type[T], effort: str = "medium") -> T:
    """Asks the model for an answer that must match output_type's schema, and returns it validated."""
    if not is_configured():
        raise LLMNotConfigured("Falta la variable de entorno ANTHROPIC_API_KEY")
    try:
        response = get_client().beta.messages.parse(
            model=model_name(),
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=output_type,
            output_config={"effort": effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise LLMError("La clave ANTHROPIC_API_KEY no es válida") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Se alcanzó el límite de uso de la API de IA; intenta de nuevo en unos minutos") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"La API de IA respondió con un error ({e.status_code})") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("No se pudo contactar a la API de IA") from e
    except ValidationError as e:
        raise LLMError("La IA no devolvió una respuesta válida") from e

    if response.stop_reason == "refusal":
        raise LLMError("La IA declinó procesar este contenido")
    if response.parsed_output is None:
        raise LLMError("La IA no devolvió una respuesta válida")
    return response.parsed_output
