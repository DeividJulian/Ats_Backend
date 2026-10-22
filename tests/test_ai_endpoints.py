"""AI features (evaluation, resume extraction, job draft) with Groq simulated at the HTTP level."""
import json

import pytest

from services import llm
from tests.test_ai_providers import EVALUATION, provider  # noqa: F401 (fixture)


@pytest.fixture
def groq(provider):  # noqa: F811
    provider["use"]("groq")
    return provider


def test_status_without_key(client):
    default = llm.PROVIDERS[llm.DEFAULT_PROVIDER]
    assert client.get("/ai/status").json() == {
        "configured": False, "provider": llm.DEFAULT_PROVIDER, "model": default.default_model,
    }


def test_without_key_returns_503(client, demo_data):
    for r in (
        client.post("/ai/evaluate/1"),
        client.post("/ai/extract-resume", json={"text": "Contador con 5 años de experiencia"}),
        client.post("/ai/draft-job", json={"title": "Auxiliar contable"}),
    ):
        assert r.status_code == 503
        assert "AI_API_KEY" in r.json()["detail"]


def test_evaluate_application(client, demo_data, groq):
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 200
    body = r.json()
    assert body["recommendation"] == "advance"
    assert body["system_score"] == client.get("/applications/1").json()["score"]
    assert len(body["interview_questions"]) == 3

    sent = groq["requests"][0]
    assert sent["body"]["model"] == llm.PROVIDERS["groq"].default_model
    assert sent["body"]["response_format"]["type"] == "json_schema"
    prompt = sent["body"]["messages"][1]["content"]
    assert "<resume>" in prompt and "FastAPI" in prompt
    # The candidate's name and email never reach the model
    assert "Camila" not in json.dumps(sent["body"]) and "camila.ortega@example.com" not in json.dumps(sent["body"])


def test_evaluate_missing_application_returns_404(client, groq):
    assert client.post("/ai/evaluate/99").status_code == 404
    assert groq["requests"] == []


def test_extract_resume_normalizes_the_answer(client, groq):
    groq["reply"] = {"skills": ["Postgres", "EXCEL", "Excel"], "experience_years": 99,
                     "education_level": "professional", "summary": "Contador con experiencia."}
    r = client.post("/ai/extract-resume", json={"text": "Contador público con 5 años en Excel y Postgres"})
    assert r.status_code == 200
    assert r.json()["skills"] == ["excel", "postgresql"]
    assert r.json()["experience_years"] == 45


def test_draft_job(client, groq):
    groq["reply"] = {"description": "Apoyo al área contable.", "requirements": "Contabilidad y Siigo",
                     "required_skills": ["Contabilidad", "Siigo", "facturacion"], "min_experience_years": 2,
                     "min_education_level": "technician"}
    r = client.post("/ai/draft-job", json={"title": "Auxiliar contable", "notes": "pyme comercial"})
    assert r.status_code == 200
    assert r.json()["required_skills"] == ["contabilidad", "facturación", "siigo"]
    # Only a suggestion: nothing is saved
    assert client.get("/jobs").json() == []
