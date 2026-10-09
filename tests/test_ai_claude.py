"""Claude features, with the Anthropic API simulated at the HTTP level (no real key or network needed)."""
import json

import anthropic
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
def claude(monkeypatch):
    """Points the SDK at a fake API. Set `reply` (dict, or (status, body)) and read `requests` afterwards."""
    state = {"reply": EVALUATION, "stop_reason": "end_turn", "requests": []}

    def handler(request: httpx2.Request) -> httpx2.Response:
        state["requests"].append({"headers": request.headers, "body": json.loads(request.content)})
        if isinstance(state["reply"], tuple):
            status, body = state["reply"]
            return httpx2.Response(status, json=body)
        return httpx2.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant", "model": llm.model_name(),
            "content": [{"type": "text", "text": json.dumps(state["reply"])}],
            "stop_reason": state["stop_reason"], "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 50},
        })

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_client", anthropic.Anthropic(
        api_key="test-key", max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    ))
    return state


def test_status_without_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert client.get("/ai/status").json() == {"configured": False, "model": llm.DEFAULT_MODEL}


def test_without_key_returns_503(client, demo_data, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for r in (
        client.post("/ai/evaluate/1"),
        client.post("/ai/extract-resume", json={"text": "Contador con 5 años de experiencia"}),
        client.post("/ai/draft-job", json={"title": "Auxiliar contable"}),
    ):
        assert r.status_code == 503
        assert "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_evaluate_application(client, demo_data, claude):
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 200
    body = r.json()
    assert body["recommendation"] == "advance"
    assert body["system_score"] == client.get("/applications/1").json()["score"]
    assert len(body["interview_questions"]) == 3

    sent = claude["requests"][0]
    assert sent["body"]["model"] == llm.DEFAULT_MODEL
    assert sent["body"]["fallbacks"] == "default"
    assert llm.FALLBACK_BETA in sent["headers"]["anthropic-beta"]
    assert sent["body"]["output_config"]["effort"] == "medium"
    assert sent["body"]["output_config"]["format"]["type"] == "json_schema"
    prompt = sent["body"]["messages"][0]["content"]
    assert "<resume>" in prompt and "FastAPI" in prompt
    # The candidate's name and email never reach the model
    assert "Camila" not in json.dumps(sent["body"]) and "camila.ortega@example.com" not in json.dumps(sent["body"])


def test_evaluate_missing_application_returns_404(client, claude):
    assert client.post("/ai/evaluate/99").status_code == 404
    assert claude["requests"] == []


def test_extract_resume_normalizes_the_answer(client, claude):
    claude["reply"] = {"skills": ["Postgres", "EXCEL", "Excel"], "experience_years": 99,
                       "education_level": "professional", "summary": "Contador con experiencia."}
    r = client.post("/ai/extract-resume", json={"text": "Contador público con 5 años en Excel y Postgres"})
    assert r.status_code == 200
    assert r.json()["skills"] == ["excel", "postgresql"]
    assert r.json()["experience_years"] == 45


def test_draft_job(client, claude):
    claude["reply"] = {"description": "Apoyo al área contable.", "requirements": "Contabilidad y Siigo",
                       "required_skills": ["Contabilidad", "Siigo", "facturacion"], "min_experience_years": 2,
                       "min_education_level": "technician"}
    r = client.post("/ai/draft-job", json={"title": "Auxiliar contable", "notes": "pyme comercial"})
    assert r.status_code == 200
    assert r.json()["required_skills"] == ["contabilidad", "facturación", "siigo"]
    assert claude["requests"][0]["body"]["output_config"]["effort"] == "low"
    assert client.get("/jobs").json() == []


def test_refusal_returns_502(client, demo_data, claude):
    claude["stop_reason"] = "refusal"
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502 and "declinó" in r.json()["detail"]


def test_invalid_answer_returns_502(client, demo_data, claude):
    claude["reply"] = {**EVALUATION, "recommendation": "contratar ya"}
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502


@pytest.mark.parametrize("status, expected", [(401, "no es válida"), (429, "límite"), (500, "500")])
def test_api_errors_return_502(client, demo_data, claude, status, expected):
    claude["reply"] = (status, {"type": "error", "error": {"type": "api_error", "message": "boom"}})
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 502
    assert expected in r.json()["detail"]
