import pytest

import config
from services.mailer import OUTBOX

ADMIN = {"email": "administrador@gmail.com", "password": "demo 123"}
CANDIDATE = {"email": "usuario@gmail.com", "password": "demo 123"}


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(config, "DEMO_LOGIN", True)


def test_demo_is_off_by_default(anon):
    assert anon.get("/auth/demo").json() == {"enabled": False}
    r = anon.post("/auth/demo-login", json=ADMIN)
    assert r.status_code == 404 and "desactivado" in r.json()["detail"]


def test_demo_admin_enters_with_the_password(anon, demo_on):
    assert anon.get("/auth/demo").json() == {"enabled": True}
    r = anon.post("/auth/demo-login", json=ADMIN)
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["role"] == "admin" and user["verified"] is True
    token = r.json()["access_token"]
    assert anon.get("/users", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_demo_candidate_gets_a_profile(anon, demo_on):
    r = anon.post("/auth/demo-login", json={**CANDIDATE, "email": "Usuario@Gmail.com"})
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["role"] == "candidate" and user["candidate_id"] is not None
    # Entering again uses the same account
    again = anon.post("/auth/demo-login", json=CANDIDATE).json()["user"]
    assert again["id"] == user["id"]


@pytest.mark.parametrize("body", [
    {**ADMIN, "password": "demo123"},
    {**ADMIN, "password": ""},
    {"email": "otro@gmail.com", "password": "demo 123"},
])
def test_wrong_password_or_non_demo_email_is_rejected(anon, demo_on, body):
    r = anon.post("/auth/demo-login", json=body)
    assert r.status_code == 401 and "incorrectos" in r.json()["detail"]


def test_demo_accounts_never_receive_emails(anon, demo_on):
    anon.post("/auth/demo-login", json=ADMIN)
    OUTBOX.clear()
    assert anon.post("/auth/login", json={"email": ADMIN["email"]}).status_code == 409
    r = anon.post("/auth/register", json={"name": "Alguien", "email": CANDIDATE["email"]})
    assert r.status_code == 409 and "contraseña" in r.json()["detail"]
    assert OUTBOX == []


def test_deactivated_demo_account_cannot_enter(client, anon, demo_on):
    demo_id = anon.post("/auth/demo-login", json=CANDIDATE).json()["user"]["id"]
    assert client.patch(f"/users/{demo_id}", json={"is_active": False}).status_code == 200
    assert anon.post("/auth/demo-login", json=CANDIDATE).status_code == 403
