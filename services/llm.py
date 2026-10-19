"""Provider-independent client for the language model, with schema-validated (structured) outputs.

Environment variables:
  AI_PROVIDER  gemini | groq | anthropic (default gemini)
  AI_API_KEY   API key of that provider (required to use the AI features)
  AI_MODEL     optional model override (each provider has a default)
  AI_BASE_URL  optional endpoint override (each provider has a default)

Compatibility: with ANTHROPIC_API_KEY set and no AI_API_KEY, Anthropic is used as before
(ANTHROPIC_MODEL still works as the model override).
"""
import os
from dataclasses import dataclass
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

TIMEOUT_SECONDS = 30
# If a safety classifier declines a request, the API re-runs it on a recommended fallback model
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class Provider:
    label: str
    default_model: str
    default_base_url: str | None


PROVIDERS = {
    "anthropic": Provider("Claude (Anthropic)", "claude-opus-5-5", None),
}
DEFAULT_PROVIDER = "anthropic"

T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None


class LLMNotConfigured(Exception):
    """There is no API key (or the provider name is unknown). The message is shown to the user."""


class LLMError(Exception):
    """The API failed or returned an unusable answer. The message is shown to the user, so it is in Spanish."""


@dataclass(frozen=True)
class AIConfig:
    provider: str
    api_key: str
    model: str
    base_url: str | None


def current_config() -> AIConfig:
    """Reads the environment on every call, so a change of variables needs no code change."""
    api_key = (os.getenv("AI_API_KEY") or "").strip()
    legacy_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key and legacy_key:
        model = os.getenv("AI_MODEL") or os.getenv("ANTHROPIC_MODEL") or PROVIDERS["anthropic"].default_model
        return AIConfig("anthropic", legacy_key, model, None)

    provider = (os.getenv("AI_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    spec = PROVIDERS.get(provider)
    model = os.getenv("AI_MODEL") or (spec.default_model if spec else "")
    base_url = os.getenv("AI_BASE_URL") or (spec.default_base_url if spec else None)
    return AIConfig(provider, api_key, model, base_url)


def provider_name() -> str:
    return current_config().provider


def model_name() -> str:
    return current_config().model


def is_configured() -> bool:
    config = current_config()
    return config.provider in PROVIDERS and bool(config.api_key)


def _check(config: AIConfig) -> None:
    if config.provider not in PROVIDERS:
        raise LLMNotConfigured(f"AI_PROVIDER no es válido: usa uno de {', '.join(PROVIDERS)}")
    if not config.api_key:
        raise LLMNotConfigured("falta AI_API_KEY en el servidor")


def get_client(api_key: str) -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=1)
    return _client


def _generate_anthropic(config: AIConfig, system: str, user: str, output_type: type[T], effort: str) -> T:
    try:
        response = get_client(config.api_key).beta.messages.parse(
            model=config.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=output_type,
            output_config={"effort": effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise LLMError("La clave de la API de IA no es válida") from e
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


def generate(system: str, user: str, output_type: type[T], effort: str = "medium") -> T:
    """Asks the model for an answer that must match output_type's schema, and returns it validated."""
    config = current_config()
    _check(config)
    return _generate_anthropic(config, system, user, output_type, effort)
