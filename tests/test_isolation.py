"""Each candidate sees and changes only their own data; the selection team shares the rest."""
from sqlalchemy import create_engine, inspect, text

from migrate_auth import upgrade_auth_schema
from tests.conftest import register


def two_candidates(client):
    ana = register("Ana Ruiz", "ana@mail.com")
    luis = register("Luis Mora", "luis@mail.com")
    ana.put("/me/profile", json={"name": "Ana Ruiz", "phone": "3001112233", "resume_text": "Contadora con Excel y Siigo", "skills": ["excel"]})
    return ana, luis


def test_each_candidate_reads_only_their_own_profile(client, demo_data):
    ana, luis = two_candidates(client)
    assert ana.get("/me/profile").json()["email"] == "ana@mail.com"
    luis_profile = luis.get("/me/profile").json()
    assert luis_profile["email"] == "luis@mail.com" and luis_profile["phone"] is None
    # Candidate profiles of others are staff-only
    assert luis.get(f"/candidates/{ana.get('/me/profile').json()['id']}").status_code == 403


def test_a_candidate_cannot_see_or_withdraw_someone_elses_application(client, demo_data):
    ana, luis = two_candidates(client)
    application = ana.post("/me/applications", json={"job_id": 3}).json()
    assert luis.get("/me/applications").json() == []
    assert luis.delete(f"/me/applications/{application['id']}").status_code == 404
    assert [a["id"] for a in ana.get("/me/applications").json()] == [application["id"]]


def test_a_candidate_cannot_reach_staff_data_or_other_users(client, demo_data):
    ana, _ = two_candidates(client)
    for path in ("/candidates", "/applications", "/users", "/jobs/1/ranking"):
        assert ana.get(path).status_code == 403, path
    assert ana.patch("/users/1", json={"name": "Otro"}).status_code == 403


def test_the_selection_team_shares_jobs_and_candidates(client, demo_data):
    from tests.conftest import login

    client.post("/users", json={"name": "Laura Gómez", "email": "laura@empresa.com", "role": "recruiter"})
    laura = login("laura@empresa.com")
    assert len(laura.get("/jobs").json()) == len(client.get("/jobs").json()) == 3
    assert laura.get("/candidates").status_code == 200


def test_migration_keeps_existing_accounts_and_is_repeatable(tmp_path):
    """The old Neon schema (password required, no verified column) is upgraded without losing rows."""
    engine = create_engine(f"sqlite:///{tmp_path / 'vieja.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE candidates (id INTEGER PRIMARY KEY)"))
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, "
            "password_hash TEXT NOT NULL, role TEXT NOT NULL, candidate_id INTEGER, is_active BOOLEAN NOT NULL, "
            "created_at DATETIME NOT NULL)"
        ))
        conn.execute(text("INSERT INTO users VALUES (1, 'Ana', 'ana@x.com', 'hash', 'admin', NULL, 1, '2026-10-01')"))

    changes = upgrade_auth_schema(engine)
    assert any("verified" in c for c in changes) and any("verification_codes" in c for c in changes)
    assert upgrade_auth_schema(engine) == []
    with engine.connect() as conn:
        assert conn.execute(text("SELECT email, verified FROM users")).all() == [("ana@x.com", 1)]
    assert "verification_codes" in inspect(engine).get_table_names()
