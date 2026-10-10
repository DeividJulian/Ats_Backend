import pytest
from fastapi.testclient import TestClient

from main import app
from services.seed import DEMO_PASSWORD, DEMO_RECRUITER
from tests.conftest import ADMIN, login


def test_login_returns_token_and_user(anon, admin_id):
    r = anon.post("/auth/login", json={"email": "ADMIN@test.com", "password": ADMIN["password"]})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["role"] == "admin"
    assert "password_hash" not in body["user"]


def test_wrong_password_and_unknown_email_get_the_same_answer(anon, admin_id):
    wrong = anon.post("/auth/login", json={"email": ADMIN["email"], "password": "otra-clave"})
    unknown = anon.post("/auth/login", json={"email": "nadie@test.com", "password": "otra-clave"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Correo o contraseña incorrectos"}


def test_register_creates_candidate_with_profile(anon):
    r = anon.post("/auth/register", json={"name": "Juan Pérez", "email": "Juan@Mail.com", "password": "Clave1234"})
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["role"] == "candidate" and user["email"] == "juan@mail.com" and user["candidate_id"]
    me = TestClient(app, headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.get("/me/profile").json()["name"] == "Juan Pérez"


def test_register_rejects_duplicates_and_short_passwords(anon, demo_data):
    data = {"name": "Juan Pérez", "email": "juan@mail.com", "password": "Clave1234"}
    assert anon.post("/auth/register", json=data).status_code == 201
    assert anon.post("/auth/register", json=data).status_code == 409
    # A candidate profile created by a recruiter can't be claimed by just knowing the email
    assert anon.post("/auth/register", json={**data, "email": "andres.molina@example.com"}).status_code == 409
    short = anon.post("/auth/register", json={**data, "email": "otro@mail.com", "password": "corta"})
    assert short.status_code == 422


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


def test_recruiter_permissions(demo_data):
    recruiter = login(DEMO_RECRUITER[1], DEMO_PASSWORD)
    assert recruiter.get("/jobs").status_code == 200
    assert recruiter.get("/jobs/1/ranking").status_code == 200
    assert recruiter.get("/users").status_code == 403
    assert recruiter.post("/seed?reset=true").status_code == 403
    assert recruiter.get("/me/profile").status_code == 403


def test_candidate_permissions(demo_data):
    candidate = login("camila.ortega@example.com", DEMO_PASSWORD)
    for path in ("/jobs", "/candidates", "/applications", "/stats", "/jobs/1/ranking", "/users"):
        r = candidate.get(path)
        assert r.status_code == 403, path
        assert r.json()["detail"] == "No tienes permiso para esta acción"
    assert candidate.get("/me/profile").status_code == 200


def test_seed_creates_demo_accounts(demo_data):
    assert {a["role"] for a in demo_data["demo_accounts"]} == {"recruiter", "candidate"}
    login(DEMO_RECRUITER[1], DEMO_PASSWORD)


def test_reset_keeps_admins_but_removes_other_accounts(client, demo_data, anon):
    anon.post("/auth/register", json={"name": "Juan Pérez", "email": "juan@mail.com", "password": "Clave1234"})
    assert client.post("/seed?reset=true").status_code == 200
    emails = {u["email"] for u in client.get("/users").json()}
    assert ADMIN["email"] in emails and "juan@mail.com" not in emails
    assert client.get("/jobs/1").status_code == 200


def test_initial_admin_from_environment(monkeypatch):
    from database import SessionLocal
    from models.user import User
    from services.bootstrap import ensure_admin

    monkeypatch.setenv("ADMIN_EMAIL", "Jefe@Empresa.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "Jefe12345")
    with SessionLocal() as db:
        ensure_admin(db)
        ensure_admin(db)  # running it again does not duplicate the account
        admins = db.query(User).filter(User.role == "admin").all()
    assert [a.email for a in admins] == ["jefe@empresa.com"]
    login("jefe@empresa.com", "Jefe12345")
