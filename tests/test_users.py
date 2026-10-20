from tests.conftest import last_code, login, register

RECRUITER = {"name": "Laura Gómez", "email": "laura@empresa.com", "role": "recruiter"}


def test_admin_creates_staff_accounts(client):
    r = client.post("/users", json=RECRUITER)
    assert r.status_code == 201 and r.json()["role"] == "recruiter"
    # Not usable until that person enters with the code sent to their email
    assert r.json()["verified"] is False
    assert client.post("/users", json=RECRUITER).status_code == 409
    assert login(RECRUITER["email"]).get("/auth/me").json()["verified"] is True


def test_admin_cannot_create_candidates_directly(client):
    assert client.post("/users", json={**RECRUITER, "role": "candidate"}).status_code == 422


def test_staff_accounts_no_longer_take_passwords(client):
    user = client.post("/users", json={**RECRUITER, "password": "Laura1234"}).json()
    assert "password" not in user and "password_hash" not in user


def test_deactivated_user_cannot_log_in_or_use_old_tokens(client, anon):
    user = client.post("/users", json=RECRUITER).json()
    session = login(RECRUITER["email"])
    assert client.patch(f"/users/{user['id']}", json={"is_active": False}).json()["is_active"] is False
    assert session.get("/jobs").status_code == 403
    assert anon.post("/auth/login", json={"email": RECRUITER["email"]}).status_code == 403


def test_deactivated_user_cannot_finish_a_login_started_before(client, anon):
    user = client.post("/users", json=RECRUITER).json()
    anon.post("/auth/login", json={"email": RECRUITER["email"]})
    code = last_code(RECRUITER["email"])
    client.patch(f"/users/{user['id']}", json={"is_active": False})
    assert anon.post("/auth/verify", json={"email": RECRUITER["email"], "code": code}).status_code == 403


def test_change_role(client):
    user = client.post("/users", json=RECRUITER).json()
    client.patch(f"/users/{user['id']}", json={"role": "admin"})
    assert login(RECRUITER["email"]).get("/users").status_code == 200


def test_admin_cannot_lock_themselves_out(client, admin_id):
    assert client.patch(f"/users/{admin_id}", json={"is_active": False}).status_code == 409
    assert client.patch(f"/users/{admin_id}", json={"role": "recruiter"}).status_code == 409
    assert client.delete(f"/users/{admin_id}").status_code == 409


def test_deleting_a_candidate_account_keeps_the_profile(client, demo_data):
    register("Camila Ortega", "camila.ortega@example.com")
    candidate_user = next(u for u in client.get("/users").json() if u["role"] == "candidate")
    assert client.patch(f"/users/{candidate_user['id']}", json={"role": "admin"}).status_code == 409
    assert client.delete(f"/users/{candidate_user['id']}").status_code == 200
    assert client.get(f"/candidates/{candidate_user['candidate_id']}").status_code == 200
    assert client.delete("/users/999").status_code == 404


def test_deleting_a_user_also_deletes_their_codes(client, anon):
    user = client.post("/users", json=RECRUITER).json()
    anon.post("/auth/login", json={"email": RECRUITER["email"]})
    assert client.delete(f"/users/{user['id']}").status_code == 200
    from database import SessionLocal
    from models.user import VerificationCode

    with SessionLocal() as db:
        assert db.query(VerificationCode).count() == 0
