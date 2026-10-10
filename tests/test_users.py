from tests.conftest import login

RECRUITER = {"name": "Laura Gómez", "email": "laura@empresa.com", "password": "Laura1234", "role": "recruiter"}


def test_admin_creates_staff_accounts(client):
    r = client.post("/users", json=RECRUITER)
    assert r.status_code == 201 and r.json()["role"] == "recruiter"
    assert client.post("/users", json=RECRUITER).status_code == 409
    login(RECRUITER["email"], RECRUITER["password"])


def test_admin_cannot_create_candidates_directly(client):
    assert client.post("/users", json={**RECRUITER, "role": "candidate"}).status_code == 422


def test_deactivated_user_cannot_log_in_or_use_old_tokens(client, anon):
    user = client.post("/users", json=RECRUITER).json()
    session = login(RECRUITER["email"], RECRUITER["password"])
    assert client.patch(f"/users/{user['id']}", json={"is_active": False}).json()["is_active"] is False
    assert session.get("/jobs").status_code == 403
    r = anon.post("/auth/login", json={"email": RECRUITER["email"], "password": RECRUITER["password"]})
    assert r.status_code == 403


def test_change_role_and_password(client):
    user = client.post("/users", json=RECRUITER).json()
    client.patch(f"/users/{user['id']}", json={"role": "admin", "password": "NuevaClave1"})
    assert login(RECRUITER["email"], "NuevaClave1").get("/users").status_code == 200


def test_admin_cannot_lock_themselves_out(client, admin_id):
    assert client.patch(f"/users/{admin_id}", json={"is_active": False}).status_code == 409
    assert client.patch(f"/users/{admin_id}", json={"role": "recruiter"}).status_code == 409
    assert client.delete(f"/users/{admin_id}").status_code == 409


def test_deleting_a_candidate_account_keeps_the_profile(client, demo_data):
    candidate_user = next(u for u in client.get("/users").json() if u["role"] == "candidate")
    assert client.patch(f"/users/{candidate_user['id']}", json={"role": "admin"}).status_code == 409
    assert client.delete(f"/users/{candidate_user['id']}").status_code == 200
    assert client.get(f"/candidates/{candidate_user['candidate_id']}").status_code == 200
    assert client.delete("/users/999").status_code == 404
