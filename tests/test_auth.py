import pytest
from fastapi.testclient import TestClient

from main import app
from tests.conftest import ADMIN, last_code, login, register


def test_login_sends_a_code_and_verify_returns_token_and_user(anon, admin_id):
    r = anon.post("/auth/login", json={"email": "ADMIN@test.com"})
    assert r.status_code == 200 and r.json()["email"] == ADMIN["email"]
    r = anon.post("/auth/verify", json={"email": ADMIN["email"], "code": last_code(ADMIN["email"])})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["role"] == "admin" and body["user"]["last_login"]
    assert "password_hash" not in body["user"]


def test_login_with_unknown_email_says_to_sign_up(anon):
    r = anon.post("/auth/login", json={"email": "nadie@test.com"})
    assert r.status_code == 404
    assert "crea una primero" in r.json()["detail"]


def test_register_creates_candidate_with_profile(anon):
    session = register("Juan Pérez", "Juan@Mail.com")
    user = session.get("/auth/me").json()
    assert user["role"] == "candidate" and user["email"] == "juan@mail.com" and user["candidate_id"]
    assert session.get("/me/profile").json()["name"] == "Juan Pérez"


def test_register_rejects_verified_duplicates(anon):
    register("Juan Pérez", "juan@mail.com")
    r = anon.post("/auth/register", json={"name": "Juan Pérez", "email": "juan@mail.com"})
    assert r.status_code == 409


def test_register_links_a_profile_created_by_a_recruiter(anon, demo_data, client):
    """The code proves the email is theirs, so the existing profile becomes their account."""
    profile = next(c for c in client.get("/candidates").json() if c["email"] == "andres.molina@example.com")
    session = register("Andrés Molina", "andres.molina@example.com")
    assert session.get("/auth/me").json()["candidate_id"] == profile["id"]
    assert len(client.get("/candidates").json()) == 9


def test_me_requires_a_valid_token(anon, client):
    assert anon.get("/auth/me").status_code == 401
    assert anon.get("/auth/me").json()["detail"] == "Debes iniciar sesión"
    forged = TestClient(app, headers={"Authorization": "Bearer abc.def.ghi"})
    assert forged.get("/auth/me").status_code == 401
    assert client.get("/auth/me").json()["email"] == ADMIN["email"]


@pytest.mark.parametrize("method, path", [
    ("get", "/jobs"), ("get", "/candidates"), ("get", "/applications"), ("get", "/stats"),
    ("get", "/jobs/1/ranking"), ("post", "/nlp/analyze-text"), ("get", "/ai/status"), ("post", "/seed"),
    ("get", "/users"), ("get", "/me/profile"),
])
def test_protected_endpoints_need_a_session(anon, method, path):
    assert getattr(anon, method)(path).status_code == 401


def test_public_endpoints_need_no_session(anon, demo_data):
    jobs = anon.get("/public/jobs").json()
    assert len(jobs) == 3 and "status" not in jobs[0]
    assert anon.get("/public/jobs/1").json()["title"] == "Desarrollador Backend Python Junior"
    assert anon.get("/public/summary").json() == {"open_jobs": 3, "candidates": 9, "hires": 0}
    assert anon.get("/health").status_code == 200


def test_closed_jobs_are_not_public(client, anon, demo_data):
    client.patch("/jobs/1/status", json={"status": "closed"})
    assert [j["id"] for j in anon.get("/public/jobs").json()] == [3, 2]
    assert anon.get("/public/jobs/1").status_code == 404


def test_recruiter_permissions(client, demo_data):
    client.post("/users", json={"name": "Laura Gómez", "email": "laura@empresa.com", "role": "recruiter"})
    recruiter = login("laura@empresa.com")
    assert recruiter.get("/jobs").status_code == 200
    assert recruiter.get("/jobs/1/ranking").status_code == 200
    assert recruiter.get("/users").status_code == 403
    assert recruiter.post("/seed?reset=true").status_code == 403
    assert recruiter.get("/me/profile").status_code == 403


def test_candidate_permissions(demo_data):
    candidate = register("Camila Ortega", "camila.ortega@example.com")
    for path in ("/jobs", "/candidates", "/applications", "/stats", "/jobs/1/ranking", "/users"):
        r = candidate.get(path)
        assert r.status_code == 403, path
        assert r.json()["detail"] == "No tienes permiso para esta acción"
    assert candidate.get("/me/profile").status_code == 200


def test_seed_creates_no_accounts(client, demo_data):
    assert "demo_accounts" not in demo_data
    assert [u["email"] for u in client.get("/users").json()] == [ADMIN["email"]]


def test_there_is_no_demo_login(anon, demo_data):
    assert anon.post("/auth/demo", json={"account": "recruiter"}).status_code == 404
    assert anon.get("/auth/options").status_code == 404


def test_reset_keeps_admins_but_removes_other_accounts(client, demo_data, anon):
    register("Juan Pérez", "juan@mail.com")
    assert client.post("/seed?reset=true").status_code == 200
    emails = {u["email"] for u in client.get("/users").json()}
    assert ADMIN["email"] in emails and "juan@mail.com" not in emails
    assert client.get("/jobs/1").status_code == 200


def test_initial_admin_from_environment(monkeypatch):
    from database import SessionLocal
    from models.user import User
    from services.bootstrap import ensure_admin

    monkeypatch.setenv("ADMIN_EMAIL", "Jefe@Empresa.com")
    with SessionLocal() as db:
        ensure_admin(db)
        ensure_admin(db)  # running it again does not duplicate the account
        admins = db.query(User).filter(User.role == "admin").all()
    assert [a.email for a in admins] == ["jefe@empresa.com"]
    # No password: the admin enters with the code sent to that email
    assert login("jefe@empresa.com").get("/users").status_code == 200
