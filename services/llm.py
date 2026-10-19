"""Provider-independent client for the language model, with schema-validated (structured) outputs.

Environment variables:
  AI_PROVIDER  gemini | groq | anthropic (default gemini)
  AI_API_KEY   API key of that provider (required to use the AI features)
  AI_MODEL     optional model override (each provider has a default)
  AI_BASE_URL  optional endpoint override (each provider has a default)

Compatibility: with ANTHROPIC_API_KEY set and no AI_API_KEY, Anthropic is used as before
(ANTHROPIC_MODEL still works as the model override).
"""
import copy
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, TypeVar

import anthropic
import httpx2
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("ats.ai")

TIMEOUT_SECONDS = 30
# If a safety classifier declines a request, the API re-runs it on a recommended fallback model
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class Provider:
    label: str
    default_model: str
    default_base_url: str | None


# Gemini and Groq are called through their OpenAI-compatible endpoints (POST {base_url}/chat/completions)
PROVIDERS = {
    "gemini": Provider("Gemini (Google)", "gemini-3.8-flash", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "groq": Provider("Groq", "openai/gpt-oss-20b", "https://api.groq.com/openai/v1"),
    "anthropic": Provider("Claude (Anthropic)", "claude-opus-5-5", None),
}
DEFAULT_PROVIDER = "gemini"

T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None
_http: httpx2.Client | None = None


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


def strict_schema(output_type: type[BaseModel]) -> dict[str, Any]:
    """JSON schema of a Pydantic model in the strict form of OpenAI-style structured outputs:
    every object lists all its properties as required and allows no extra ones."""
    schema = copy.deepcopy(output_type.model_json_schema())

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def get_http() -> httpx2.Client:
    global _http
    if _http is None:
        _http = httpx2.Client(timeout=TIMEOUT_SECONDS)
    return _http


def _without_code_fence(text: str) -> str:
    """Some models wrap the JSON in ```json ... ``` even when asked for raw JSON."""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)


def _generate_openai_compatible(config: AIConfig, system: str, user: str, output_type: type[T]) -> T:
    url = config.base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": config.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": output_type.__name__.strip("_").lower(), "strict": True, "schema": strict_schema(output_type)},
        },
    }
    response = get_http().post(url, json=body, headers={"Authorization": f"Bearer {config.api_key}"})
    if response.status_code != 200:
        logger.warning("El proveedor %s respondió %s: %s", config.provider, response.status_code, response.text[:300])
        raise LLMError(f"La API de IA respondió con un error ({response.status_code})")

    try:
        choice = response.json()["choices"][0]
        message = choice["message"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError("La IA no devolvió una respuesta válida") from e
    if message.get("refusal") or choice.get("finish_reason") == "content_filter":
        raise LLMError("La IA declinó procesar este contenido")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMError("La IA no devolvió una respuesta válida")
    try:
        return output_type.model_validate_json(_without_code_fence(content))
    except ValidationError as e:
        raise LLMError("La IA no devolvió una respuesta válida") from e


def generate(system: str, user: str, output_type: type[T], effort: str = "medium") -> T:
    """Asks the model for an answer that must match output_type's schema, and returns it validated.
    effort only applies to Anthropic models."""
    config = current_config()
    _check(config)
    if config.provider == "anthropic":
        return _generate_anthropic(config, system, user, output_type, effort)
    return _generate_openai_compatible(config, system, user, output_type)
