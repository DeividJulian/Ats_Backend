"""Provider-independent client for the language model, with schema-validated (structured) outputs.

Environment variables:
  AI_PROVIDER  groq | gemini (default groq)
  AI_API_KEY   API key of that provider (required to use the AI features)
  AI_MODEL     optional model override (each provider has a default)
  AI_BASE_URL  optional endpoint override (each provider has a default)
  AI_FALLBACK_MODEL  lighter model used when the main one is busy, out of quota or too slow
               (Gemini: gemini-flash-lite-latest by default; "none" turns it off)
"""
import copy
import dataclasses
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx2
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("ats.ai")

TIMEOUT_SECONDS = 30
# With a fallback model, the main one gets less time: when it is busy it is often just slow
PRIMARY_TIMEOUT_SECONDS = 15
RETRYABLE_STATUS = {500, 502, 503, 504}
RETRY_DELAY_SECONDS = 1.5


@dataclass(frozen=True)
class Provider:
    label: str
    default_model: str
    default_base_url: str | None
    # Lighter model to try when the main one is overloaded (503), out of free quota (429) or too slow
    default_fallback: str | None = None


# Both are called through their OpenAI-compatible endpoints (POST {base_url}/chat/completions)
PROVIDERS = {
    # gemini-flash-lite-latest is an alias Google keeps pointing to its current lite model, with a larger free quota
    "gemini": Provider(
        "Gemini (Google)", "gemini-3.8-flash", "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-flash-lite-latest",
    ),
    "groq": Provider("Groq", "openai/gpt-oss-20b", "https://api.groq.com/openai/v1"),
}
DEFAULT_PROVIDER = "groq"

T = TypeVar("T", bound=BaseModel)

_http: httpx2.Client | None = None


class LLMNotConfigured(Exception):
    """There is no API key (or the provider name is unknown). The message is shown to the user."""


class LLMError(Exception):
    """The API failed or returned an unusable answer. The message is shown to the user, so it is in Spanish."""


class LLMUnavailable(LLMError):
    """The provider is overloaded (5xx) or did not answer in time: another model may still work."""


class LLMRateLimited(LLMError):
    """The provider's usage limit was reached (HTTP 429). retry_after: seconds to wait, if the provider said."""

    def __init__(self, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def _label(config: "AIConfig") -> str:
    spec = PROVIDERS.get(config.provider)
    return spec.label if spec else config.provider


def _status_error(config: "AIConfig", status: int, retry_after: str | None = None) -> LLMError:
    """Same Spanish message for the same problem, whatever the provider."""
    name = _label(config)
    if status == 429:
        return LLMRateLimited(
            f"Se alcanzó el límite de uso de {name}. Espera unos minutos y vuelve a intentarlo.", retry_after
        )
    if status in (401, 403):
        return LLMError(f"La clave de {name} no es válida o no tiene permisos (revisa AI_API_KEY)")
    if status == 404:
        return LLMError(f"{name} no reconoce el modelo configurado (revisa AI_MODEL)")
    if status >= 500:
        return LLMUnavailable(f"El servicio de {name} no está disponible en este momento ({status}). Intenta más tarde.")
    return LLMError(f"{name} rechazó la solicitud ({status})")


@dataclass(frozen=True)
class AIConfig:
    provider: str
    api_key: str
    model: str
    base_url: str | None
    fallback_model: str | None = None


def current_config() -> AIConfig:
    """Reads the environment on every call, so a change of variables needs no code change."""
    api_key = (os.getenv("AI_API_KEY") or "").strip()
    provider = (os.getenv("AI_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    spec = PROVIDERS.get(provider)
    model = os.getenv("AI_MODEL") or (spec.default_model if spec else "")
    base_url = os.getenv("AI_BASE_URL") or (spec.default_base_url if spec else None)
    fallback = (os.getenv("AI_FALLBACK_MODEL") or (spec.default_fallback if spec else "") or "").strip()
    if fallback.lower() in ("", "none", "no", "false") or fallback == model:
        fallback = None
    return AIConfig(provider, api_key, model, base_url, fallback)


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


def _generate_openai_compatible(
    config: AIConfig, system: str, user: str, output_type: type[T], retry: bool = True, timeout: float | None = None
) -> T:
    url = config.base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": config.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": output_type.__name__.strip("_").lower(), "strict": True, "schema": strict_schema(output_type)},
        },
    }
    for attempt in range(2 if retry else 1):
        try:
            response = get_http().post(
                url, json=body, headers={"Authorization": f"Bearer {config.api_key}"}, timeout=timeout or TIMEOUT_SECONDS
            )
        except httpx2.TimeoutException as e:
            raise LLMUnavailable(f"{_label(config)} tardó demasiado en responder. Intenta de nuevo.") from e
        except httpx2.HTTPError as e:
            raise LLMError(f"No se pudo contactar a {_label(config)}") from e
        # A busy provider (5xx) often answers on a second try; usage limits (429) are not retried
        if response.status_code in RETRYABLE_STATUS and retry and attempt == 0:
            logger.info("El proveedor %s respondió %s: se reintenta una vez", config.provider, response.status_code)
            time.sleep(RETRY_DELAY_SECONDS)
            continue
        break
    if response.status_code != 200:
        # The provider's message helps to diagnose (it never contains the API key)
        logger.warning("El proveedor %s respondió %s: %s", config.provider, response.status_code, response.text[:300])
        raise _status_error(config, response.status_code, response.headers.get("retry-after"))

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


def generate(system: str, user: str, output_type: type[T]) -> T:
    """Asks the model for an answer that must match output_type's schema, and returns it validated."""
    config = current_config()
    _check(config)
    if not config.fallback_model:
        return _generate_openai_compatible(config, system, user, output_type)
    # One try with the main model; if it is busy, out of quota or slow, the lighter model answers instead
    try:
        return _generate_openai_compatible(config, system, user, output_type, retry=False, timeout=PRIMARY_TIMEOUT_SECONDS)
    except (LLMUnavailable, LLMRateLimited) as e:
        logger.info("%s falló (%s): se usa el modelo de respaldo %s", config.model, e, config.fallback_model)
    return _generate_openai_compatible(dataclasses.replace(config, model=config.fallback_model), system, user, output_type)
