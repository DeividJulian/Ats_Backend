"""Gemini and Groq through their OpenAI-compatible endpoint, simulated at the HTTP level."""
import json

import httpx2
import pytest

from services import llm
from tests.test_ai_claude import EVALUATION


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
    use("gemini")
    monkeypatch.setattr(llm, "_http", httpx2.Client(transport=httpx2.MockTransport(handler)))
    state["use"] = use
    return state


def test_gemini_is_the_default_provider(client, provider, monkeypatch):
    monkeypatch.delenv("AI_PROVIDER")
    body = client.get("/ai/status").json()
    assert body == {"configured": True, "provider": "gemini", "model": "gemini-3.8-flash"}


def test_evaluate_with_gemini(client, demo_data, provider):
    r = client.post("/ai/evaluate/1")
    assert r.status_code == 200
    assert r.json()["recommendation"] == "advance"
    sent = provider["requests"][0]
    assert sent["body"]["response_format"]["type"] == "json_schema"
    schema = sent["body"]["response_format"]["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
