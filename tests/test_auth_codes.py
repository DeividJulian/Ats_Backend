"""Rules of the passwordless login: one-time codes by email, sessions and email delivery."""
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import config
from database import SessionLocal
from main import app
from models.candidate import Candidate
from models.user import User, VerificationCode
from services import codes, mailer
from services.mailer import OUTBOX, MailError
from services.security import create_token
from tests.conftest import last_code, register

JUAN = {"name": "Juan Pérez", "email": "juan@mail.com"}


def verify(anon, email, code):
    return anon.post("/auth/verify", json={"email": email, "code": code})


def test_register_emails_a_code_and_leaves_the_account_unverified(anon):
    r = anon.post("/auth/register", json=JUAN)
    assert r.status_code == 201 and r.json()["email"] == JUAN["email"]
    assert len(OUTBOX) == 1 and OUTBOX[0]["to"] == JUAN["email"]
    assert "activar" in OUTBOX[0]["subject"] and last_code(JUAN["email"]) in OUTBOX[0]["html"]
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == JUAN["email"]).one()
        assert user.verified is False and user.role == "candidate"


def test_the_code_is_stored_only_as_a_hash(anon):
    anon.post("/auth/register", json=JUAN)
    code = last_code(JUAN["email"])
    with SessionLocal() as db:
        record = db.query(VerificationCode).one()
        assert record.code_hash != code and len(record.code_hash) == 64 and code not in record.code_hash
        assert record.purpose == "signup"


def test_verify_activates_the_account_and_returns_a_session(anon):
    anon.post("/auth/register", json=JUAN)
    r = verify(anon, JUAN["email"], last_code(JUAN["email"]))
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["verified"] is True and user["last_login"] and user["role"] == "candidate"
    session = TestClient(app, headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert session.get("/auth/me").json()["email"] == JUAN["email"]


def test_unverified_account_can_register_again_and_gets_a_new_code(anon):
    anon.post("/auth/register", json=JUAN)
    first = last_code(JUAN["email"])
    r = anon.post("/auth/register", json={**JUAN, "name": "Juan Carlos Pérez"})
    assert r.status_code == 201 and len(OUTBOX) == 2
    with SessionLocal() as db:
        assert db.query(User).count() == 1 and db.query(Candidate).count() == 1
        assert db.query(User).one().name == "Juan Carlos Pérez"
    second = last_code(JUAN["email"])
    if first != second:
        assert verify(anon, JUAN["email"], first).status_code == 400


def test_verified_account_cannot_register_again(anon):
    register(**JUAN)
    r = anon.post("/auth/register", json=JUAN)
    assert r.status_code == 409 and "inicia sesión" in r.json()["detail"]


def test_staff_email_cannot_be_used_to_sign_up_as_candidate(client, anon):
    client.post("/users", json={"name": "Laura Gómez", "email": "laura@empresa.com", "role": "recruiter"})
    assert anon.post("/auth/register", json={"name": "Laura", "email": "laura@empresa.com"}).status_code == 409


def test_uppercase_emails_are_the_same_account(anon):
    anon.post("/auth/register", json={**JUAN, "email": "  JUAN@Mail.COM "})
    assert verify(anon, "Juan@MAIL.com", last_code(JUAN["email"])).status_code == 200
    assert anon.post("/auth/register", json={**JUAN, "email": "JUAN@MAIL.COM"}).status_code == 409
    assert anon.post("/auth/login", json={"email": "JuAn@mail.com"}).json()["email"] == JUAN["email"]


def test_login_emails_a_new_code(anon):
    register(**JUAN)
    r = anon.post("/auth/login", json={"email": JUAN["email"]})
    assert r.status_code == 200 and "entrar" in OUTBOX[-1]["subject"]
    assert verify(anon, JUAN["email"], last_code(JUAN["email"])).status_code == 200


def test_login_needs_an_existing_account(anon):
    assert anon.post("/auth/login", json={"email": "nadie@mail.com"}).status_code == 404
    assert OUTBOX == []


def test_wait_between_codes(anon, monkeypatch):
    monkeypatch.setattr(config, "CODE_WAIT_SECONDS", 30)
    assert anon.post("/auth/register", json=JUAN).status_code == 201
    r = anon.post("/auth/register", json=JUAN)
    assert r.status_code == 429 and "segundos" in r.json()["detail"]
    assert 0 < int(r.headers["Retry-After"]) <= 30
    assert anon.post("/auth/login", json={"email": JUAN["email"]}).status_code == 429
    assert len(OUTBOX) == 1


def test_wrong_code_says_how_many_attempts_are_left(anon):
    anon.post("/auth/register", json=JUAN)
    good = last_code(JUAN["email"])
    wrong = "000000" if good != "000000" else "111111"
    r = verify(anon, JUAN["email"], wrong)
    assert r.status_code == 400 and r.json()["detail"] == "Código incorrecto. Te quedan 4 intentos"
    assert verify(anon, JUAN["email"], good).status_code == 200


def test_too_many_attempts_burn_the_code(anon):
    anon.post("/auth/register", json=JUAN)
    good = last_code(JUAN["email"])
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(config.CODE_ATTEMPTS - 1):
        verify(anon, JUAN["email"], wrong)
    last = verify(anon, JUAN["email"], wrong)
    assert "Agotaste los intentos" in last.json()["detail"]
    r = verify(anon, JUAN["email"], good)
    assert r.status_code == 400 and r.json()["detail"] == "No hay un código activo: pide uno nuevo"


def test_expired_code(anon):
    anon.post("/auth/register", json=JUAN)
    with SessionLocal() as db:
        record = db.query(VerificationCode).one()
        record.expires_at = codes.utc_now() - timedelta(seconds=1)
        db.commit()
    r = verify(anon, JUAN["email"], last_code(JUAN["email"]))
    assert r.status_code == 400 and r.json()["detail"] == "El código venció: pide uno nuevo"


def test_a_code_works_only_once(anon):
    anon.post("/auth/register", json=JUAN)
    code = last_code(JUAN["email"])
    assert verify(anon, JUAN["email"], code).status_code == 200
    assert verify(anon, JUAN["email"], code).status_code == 400


def test_a_new_code_invalidates_the_previous_one(anon):
    register(**JUAN)
    anon.post("/auth/login", json={"email": JUAN["email"]})
    first = last_code(JUAN["email"])
    anon.post("/auth/login", json={"email": JUAN["email"]})
    second = last_code(JUAN["email"])
    with SessionLocal() as db:
        assert db.query(VerificationCode).filter(VerificationCode.used.is_(False)).count() == 1
    if first != second:
        assert verify(anon, JUAN["email"], first).status_code == 400
    assert verify(anon, JUAN["email"], second).status_code == 200


@pytest.mark.parametrize("code", ["12345", "1234567", "abcdef", ""])
def test_malformed_codes_are_rejected(anon, code):
    assert verify(anon, JUAN["email"], code).status_code == 422


def test_invalid_tokens_get_401(anon, admin_id):
    for token in ("abc.def.ghi", create_token(admin_id, "admin", hours=-1)):
        r = TestClient(app, headers={"Authorization": f"Bearer {token}"}).get("/auth/me")
        assert r.status_code == 401 and "inicia sesión de nuevo" in r.json()["detail"]
    assert anon.get("/auth/me").status_code == 401


def test_token_signed_with_another_key_is_rejected(admin_id, monkeypatch):
    token = create_token(admin_id, "admin")
    monkeypatch.setattr(config, "SECRET_KEY", "otra-clave-distinta-0123456789abcdef")
    assert TestClient(app, headers={"Authorization": f"Bearer {token}"}).get("/auth/me").status_code == 401


def test_unverified_account_cannot_use_a_token(anon):
    anon.post("/auth/register", json=JUAN)
    with SessionLocal() as db:
        user = db.query(User).one()
    session = TestClient(app, headers={"Authorization": f"Bearer {create_token(user.id, user.role)}"})
    assert session.get("/auth/me").status_code == 401
    assert session.get("/me/profile").status_code == 401


def test_if_the_email_fails_nothing_is_saved(anon, monkeypatch):
    def broken(*args, **kwargs):
        raise MailError("Brevo no respondió")

    monkeypatch.setattr(codes, "send_email", broken)
    r = anon.post("/auth/register", json=JUAN)
    assert r.status_code == 502 and "No pudimos enviar el correo" in r.json()["detail"]
    with SessionLocal() as db:
        assert db.query(User).count() == 0
        assert db.query(Candidate).count() == 0
        assert db.query(VerificationCode).count() == 0


def test_if_the_login_email_fails_no_code_is_left(anon, monkeypatch):
    register(**JUAN)
    monkeypatch.setattr(codes, "send_email", lambda *a, **k: (_ for _ in ()).throw(MailError("caído")))
    assert anon.post("/auth/login", json={"email": JUAN["email"]}).status_code == 502
    with SessionLocal() as db:
        assert db.query(VerificationCode).filter(VerificationCode.used.is_(False)).count() == 0


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_brevo_payload(monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent.update(url=request.full_url, headers=dict(request.header_items()), body=json.loads(request.data), timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(config, "EMAIL_BACKEND", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(config, "EMAIL_FROM", "deivid@gmail.com")
    monkeypatch.setattr(config, "EMAIL_FROM_NAME", "Portal ATS")
    monkeypatch.setattr(mailer.urllib.request, "urlopen", fake_urlopen)

    mailer.send_email("juan@mail.com", "Asunto", "Texto plano", "<p>HTML</p>")
    assert sent["url"] == "https://api.brevo.com/v3/smtp/email"
    assert sent["headers"]["Api-key"] == "clave-de-prueba"
    assert sent["body"] == {
        "sender": {"name": "Portal ATS", "email": "deivid@gmail.com"},
        "to": [{"email": "juan@mail.com"}],
        "subject": "Asunto",
        "textContent": "Texto plano",
        "htmlContent": "<p>HTML</p>",
    }
    assert sent["timeout"] == 15


def test_brevo_errors_become_mail_errors(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_BACKEND", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    with pytest.raises(MailError, match="BREVO_API_KEY"):
        mailer.send_email("juan@mail.com", "Asunto", "Texto")

    def refused(request, timeout):
        raise OSError("401 Unauthorized")

    monkeypatch.setattr(config, "BREVO_API_KEY", "clave-mala")
    monkeypatch.setattr(mailer.urllib.request, "urlopen", refused)
    with pytest.raises(MailError):
        mailer.send_email("juan@mail.com", "Asunto", "Texto")


def test_unknown_email_backend_fails_clearly(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_BACKEND", "paloma")
    with pytest.raises(MailError, match="EMAIL_BACKEND desconocido"):
        mailer.send_email("juan@mail.com", "Asunto", "Texto")


def test_demo_accounts_enter_without_a_code_only_when_allowed(anon, demo_data, monkeypatch):
    assert anon.get("/auth/options").json() == {"demo_login": True}
    r = anon.post("/auth/demo", json={"account": "recruiter"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "recruiter"
    assert anon.post("/auth/demo", json={"account": "candidate"}).json()["user"]["candidate_id"]
    assert anon.post("/auth/demo", json={"account": "admin"}).status_code == 422

    monkeypatch.setattr(config, "ALLOW_DEMO_LOGIN", False)
    assert anon.get("/auth/options").json() == {"demo_login": False}
    assert anon.post("/auth/demo", json={"account": "recruiter"}).status_code == 403


def test_demo_login_needs_the_demo_data(anon):
    assert anon.post("/auth/demo", json={"account": "recruiter"}).status_code == 404
