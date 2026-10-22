"""Gemini and Groq through their OpenAI-compatible endpoint, simulated at the HTTP level."""
import json

import httpx2
import pytest

from services import llm

EVALUATION = {
    "summary": "Buen ajuste técnico para el cargo.",
    "strengths": ["Experiencia con FastAPI", "Uso diario de Docker"],
    "gaps": [],
    "recommendation": "advance",
    "interview_questions": ["¿Qué API construyó?", "¿Cómo despliega con Docker?", "¿Cómo prueba su código?"],
}


@pytest.fixture
def provider(monkeypatch):
    """Fake OpenAI-compatible API. Set `provider`, `reply` (dict, raw text, or (status, body)); read `requests`."""
    state = {"provider": "gemini", "reply": EVALUATION, "finish_reason": "stop", "requests": []}

    def handler(request: httpx2.Request) -> httpx2.Response:
        state["requests"].append({"url": str(request.url), "headers": request.headers, "body": json.loads(request.content)})
        if isinstance(state["reply"], tuple):
            status, body = state["reply"]
            return httpx2.Response(status, json=body)
        content = state["reply"] if isinstance(state["reply"], str) else json.dumps(state["reply"])
        return httpx2.Response(200, json={
            "id": "chat-test", "object": "chat.completion",
            "choices": [{"index": 0, "finish_reason": state["finish_reason"], "message": {"role": "assistant", "content": content}}],
        })

    def use(name: str) -> None:
        monkeypatch.setenv("AI_PROVIDER", name)
        state["provider"] = name

    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "RETRY_DELAY_SECONDS", 0)
    use("gemini")
    monkeypatch.setattr(llm, "_http", httpx2.Client(transport=httpx2.MockTransport(handler)))
    state["use"] = use
    return state


def test_groq_is_the_default_provider(client, provider, monkeypatch):
    monkeypatch.delenv("AI_PROVIDER")
    body = client.get("/ai/status").json()
    assert body == {"configured": True, "provider": "groq", "model": "openai/gpt-oss-20b"}


def test_status_reports_gemini_when_chosen(client, provider):
    assert client.get("/ai/status").json() == {"configured": True, "provider": "gemini", "model": "gemini-3.8-flash"}


def test_evaluate_with_gemini(client, demo_data, provider):
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 200
    assert r.json()["recommendation"] == "advance"
    sent = provider["requests"][0]
    assert sent["body"]["response_format"]["type"] == "json_schema"
    schema = sent["body"]["response_format"]["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


# ---------- Errors (any OpenAI-compatible provider) ----------

def test_invalid_json_returns_502(client, demo_data, provider):
    provider["reply"] = "esto no es JSON"
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502 and "válida" in r.json()["detail"]


def test_answer_outside_the_schema_returns_502(client, demo_data, provider):
    provider["reply"] = {**EVALUATION, "recommendation": "contratar ya"}
    assert client.post("/ai/evaluate/1").status_code == 502


def test_json_inside_a_code_fence_is_accepted(client, demo_data, provider):
    provider["reply"] = "```json\n" + json.dumps(EVALUATION) + "\n```"
    assert client.post("/ai/evaluate/1").status_code == 200


def test_content_filter_returns_502(client, demo_data, provider):
    provider["finish_reason"] = "content_filter"
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502 and "declinó" in r.json()["detail"]


def test_rate_limit_returns_429_in_spanish(client, demo_data, provider):
    provider["reply"] = (429, {"error": {"code": 429, "message": "Resource has been exhausted", "status": "RESOURCE_EXHAUSTED"}})
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 429
    assert "límite de uso de Gemini" in r.json()["detail"]


def test_rate_limit_keeps_retry_after(client, demo_data, provider, monkeypatch):
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, json={"error": {"message": "slow down"}}, headers={"Retry-After": "20"})

    monkeypatch.setattr(llm, "_http", httpx2.Client(transport=httpx2.MockTransport(handler)))
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 429 and r.headers["retry-after"] == "20"


@pytest.mark.parametrize(
    "status, expected",
    [(500, "no está disponible"), (503, "no está disponible"), (401, "no es válida"), (404, "AI_MODEL"), (400, "rechazó")],
)
def test_provider_errors_return_502(client, demo_data, provider, status, expected):
    provider["reply"] = (status, {"error": {"message": "boom"}})
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502
    assert expected in r.json()["detail"]


def test_busy_provider_is_retried_once(client, demo_data, provider, monkeypatch):
    answers = [httpx2.Response(503, json={"error": {"message": "overloaded"}})]

    def handler(request: httpx2.Request) -> httpx2.Response:
        if answers:
            return answers.pop()
        return httpx2.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(EVALUATION)}}]})

    monkeypatch.setattr(llm, "_http", httpx2.Client(transport=httpx2.MockTransport(handler)))
    assert client.post("/ai/evaluate/1").status_code == 200


def models_called(provider):
    return [r["body"]["model"] for r in provider["requests"]]


def test_without_fallback_usage_limit_and_bad_requests_are_not_retried(client, demo_data, provider, monkeypatch):
    monkeypatch.setenv("AI_FALLBACK_MODEL", "none")
    for status in (429, 400):
        provider["requests"].clear()
        provider["reply"] = (status, {"error": {"message": "no"}})
        client.post("/ai/evaluate/1")
        assert len(provider["requests"]) == 1, status
    provider["requests"].clear()
    provider["reply"] = (503, {"error": {"message": "overloaded"}})
    client.post("/ai/evaluate/1")
    assert models_called(provider) == ["gemini-3.8-flash", "gemini-3.8-flash"]


@pytest.mark.parametrize("status", [503, 429])
def test_busy_or_out_of_quota_gemini_answers_with_the_lighter_model(client, demo_data, monkeypatch, provider, status):
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        model = json.loads(request.content)["model"]
        calls.append(model)
        if model == "gemini-3.8-flash":
            return httpx2.Response(status, json={"error": {"message": "high demand"}})
        return httpx2.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(EVALUATION)}}]})

    monkeypatch.setattr(llm, "_http", httpx2.Client(transport=httpx2.MockTransport(handler)))
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 200 and r.json()["recommendation"] == "advance"
    # One try with the main model, then straight to the fallback (no time lost retrying a busy model)
    assert calls == ["gemini-3.8-flash", "gemini-flash-lite-latest"]


def test_slow_main_model_falls_back_too(client, demo_data, monkeypatch, provider):
    def handler(request: httpx2.Request) -> httpx2.Response:
        if json.loads(request.content)["model"] == "gemini-3.8-flash":
            raise httpx2.ReadTimeout("too slow", request=request)
        return httpx2.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(EVALUATION)}}]})

    monkeypatch.setattr(llm, "_http", httpx2.Client(transport=httpx2.MockTransport(handler)))
    assert client.post("/ai/evaluate/1").status_code == 200


def test_if_both_models_fail_the_error_is_clear(client, demo_data, provider):
    provider["reply"] = (503, {"error": {"message": "overloaded"}})
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502 and "no está disponible" in r.json()["detail"]
    # Main once, fallback twice (it keeps its single retry)
    assert models_called(provider) == ["gemini-3.8-flash", "gemini-flash-lite-latest", "gemini-flash-lite-latest"]


@pytest.mark.parametrize("status", [400, 401, 404])
def test_configuration_errors_do_not_use_the_fallback(client, demo_data, provider, status):
    provider["reply"] = (status, {"error": {"message": "no"}})
    assert client.post("/ai/evaluate/1").status_code == 502
    assert models_called(provider) == ["gemini-3.8-flash"]


def test_fallback_model_can_be_chosen_or_turned_off(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("AI_FALLBACK_MODEL", raising=False)
    assert llm.current_config().fallback_model == "gemini-flash-lite-latest"
    monkeypatch.setenv("AI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    assert llm.current_config().fallback_model == "gemini-3.5-flash-lite"
    monkeypatch.setenv("AI_FALLBACK_MODEL", "none")
    assert llm.current_config().fallback_model is None
    # Groq has no fallback by default, and the same model never counts as its own fallback
    monkeypatch.delenv("AI_FALLBACK_MODEL")
    monkeypatch.setenv("AI_PROVIDER", "groq")
    assert llm.current_config().fallback_model is None
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_MODEL", "gemini-flash-lite-latest")
    assert llm.current_config().fallback_model is None


def test_timeout_returns_502(client, demo_data, provider, monkeypatch):
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("too slow", request=request)

    monkeypatch.setattr(llm, "_http", httpx2.Client(transport=httpx2.MockTransport(handler)))
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502 and "tardó demasiado" in r.json()["detail"]


def test_without_key_returns_503(client, demo_data, provider, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "")
    r = client.post("/ai/draft-job", json={"title": "Auxiliar contable"})
    assert r.status_code == 503 and "AI_API_KEY" in r.json()["detail"]
    assert provider["requests"] == []


def test_unknown_provider_is_not_configured(client, provider, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    assert client.get("/ai/status").json()["configured"] is False
    r = client.post("/ai/draft-job", json={"title": "Auxiliar contable"})
    assert r.status_code == 503 and "AI_PROVIDER" in r.json()["detail"]


# ---------- Each provider: endpoint and headers ----------

def test_gemini_endpoint_and_headers(client, demo_data, provider):
    client.post("/ai/evaluate/1")
    sent = provider["requests"][0]
    assert sent["url"] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert sent["headers"]["authorization"] == "Bearer test-key"
    assert sent["body"]["model"] == "gemini-3.8-flash"


def test_groq_endpoint_and_headers(client, provider):
    provider["use"]("groq")
    provider["reply"] = {
        "description": "Apoyo contable.", "requirements": "Excel", "required_skills": ["Excel"],
        "min_experience_years": 1, "min_education_level": None,
    }
    r = client.post("/ai/draft-job", json={"title": "Auxiliar contable"})
    assert r.status_code == 200 and r.json()["required_skills"] == ["excel"]
    sent = provider["requests"][0]
    assert sent["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert sent["headers"]["authorization"] == "Bearer test-key"
    assert sent["body"]["model"] == "openai/gpt-oss-20b"
    assert sent["body"]["response_format"]["json_schema"]["strict"] is True


def test_model_and_base_url_can_be_overridden(client, provider, monkeypatch):
    monkeypatch.setenv("AI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("AI_BASE_URL", "https://proxy.example.com/v1/")
    provider["reply"] = {"skills": ["Excel"], "experience_years": 3, "education_level": "technician", "summary": "Perfil."}
    client.post("/ai/extract-resume", json={"text": "Técnico con 3 años de experiencia en Excel"})
    sent = provider["requests"][0]
    assert sent["url"] == "https://proxy.example.com/v1/chat/completions"
    assert sent["body"]["model"] == "gemini-3.5-flash-lite"
    assert client.get("/ai/status").json()["model"] == "gemini-3.5-flash-lite"


# ---------- Privacy ----------

CONTACT_RESUME = (
    "CAMILA ORTEGA\nCel +57 300 123 4567 | camila.ortega@example.com\n"
    "Ingeniera de Sistemas con 3 años de experiencia (2021-2024) en Python, FastAPI, PostgreSQL, Git y Docker."
)
PRIVATE = ("camila", "ortega", "camila.ortega@example.com", "300 123 4567")


def test_evaluation_never_sends_name_email_or_phone(client, demo_data, provider):
    # Demo candidate 1 is Camila Ortega: her resume now starts with her contact data, as PDFs do
    candidate = client.get("/candidates/1").json()
    client.put("/candidates/1", json={
        "name": candidate["name"], "email": candidate["email"], "phone": "+57 300 123 4567", "resume_text": CONTACT_RESUME,
    })
    assert client.post("/ai/evaluate/1").status_code == 200
    sent = json.dumps(provider["requests"][0]["body"], ensure_ascii=False).lower()
    for private in PRIVATE:
        assert private not in sent, private
    assert "[candidato]" in sent and "[correo]" in sent and "[teléfono]" in sent
    assert "fastapi" in sent and "2021-2024" in sent


def test_a_different_name_inside_the_resume_is_hidden_too(client, demo_data, provider):
    # Someone uploaded another person's PDF to Camila's record: that name must not reach the model either
    candidate = client.get("/candidates/1").json()
    other = "Carlos Andrés Ortega Benavides\nContador Público\ncarlos.prueba@example.com · +57 311 987 6543\nContador con 6 años de experiencia."
    client.put("/candidates/1", json={"name": candidate["name"], "email": candidate["email"], "resume_text": other})
    client.post("/ai/evaluate/1")
    sent = json.dumps(provider["requests"][0]["body"], ensure_ascii=False).lower()
    for private in ("carlos", "andrés", "benavides", "ortega", "carlos.prueba@example.com", "311 987 6543"):
        assert private not in sent, private


def test_resume_extraction_never_sends_contact_data(client, provider):
    provider["reply"] = {"skills": ["python"], "experience_years": 3, "education_level": "professional", "summary": "Perfil."}
    assert client.post("/ai/extract-resume", json={"text": CONTACT_RESUME}).status_code == 200
    sent = json.dumps(provider["requests"][0]["body"], ensure_ascii=False).lower()
    for private in PRIVATE:
        assert private not in sent, private


def test_redaction_handles_accents_and_keeps_year_ranges():
    from services.contact import extract_phone
    from services.privacy import redact_personal_data

    text = "Referencia de sebastian rojas. Trabajó de 2018-2023 en Bogotá. Correo SEBAS@MAIL.CO, tel 601 555 1234"
    clean = redact_personal_data(text, names=("Sebastián Rojas",))
    assert clean == "Referencia de [candidato] [candidato]. Trabajó de 2018-2023 en Bogotá. Correo [correo], tel [teléfono]"
    assert extract_phone("Trabajé de 2018-2023. Cel 3001234567") == "3001234567"
