JOB = {
    "title": "Analista de datos",
    "description": "Analizar información comercial y construir tableros para la gerencia.",
    "requirements": "Excel, SQL y Power BI",
    "min_experience_years": 2,
}


def test_job_infers_skills_from_text(client):
    r = client.post("/jobs", json=JOB)
    assert r.status_code == 201
    assert {"excel", "sql", "power bi"} <= set(r.json()["required_skills"])


def test_job_keeps_hand_written_skills(client):
    r = client.post("/jobs", json={**JOB, "required_skills": ["Postgres"]})
    assert r.json()["required_skills"] == ["postgresql"]


def test_invalid_job_returns_422(client):
    r = client.post("/jobs", json={**JOB, "title": "A", "min_experience_years": 99})
    assert r.status_code == 422


def test_missing_job_returns_404(client):
    assert client.get("/jobs/999").status_code == 404


def test_close_job(client):
    job = client.post("/jobs", json=JOB).json()
    r = client.patch(f"/jobs/{job['id']}/status", json={"status": "closed"})
    assert r.json()["status"] == "closed"
    assert len(client.get("/jobs?status=open").json()) == 0


def test_candidate_profile_is_extracted_from_resume(client):
    r = client.post(
        "/candidates",
        json={
            "name": "Ana Ruiz",
            "email": "ana@example.com",
            "resume_text": "Ingeniera de sistemas con 4 años de experiencia en Python y Docker",
        },
    )
    assert r.status_code == 201
    candidate = r.json()
    assert {"python", "docker"} <= set(candidate["skills"])
    assert candidate["experience_years"] == 4
    assert candidate["education_level"] == "professional"


def test_manual_data_takes_priority(client):
    r = client.post(
        "/candidates",
        json={"name": "Ana Ruiz", "email": "ana@example.com", "resume_text": "5 años de experiencia", "experience_years": 1},
    )
    assert r.json()["experience_years"] == 1


def test_duplicate_email_returns_409(client):
    data = {"name": "Ana Ruiz", "email": "ana@example.com"}
    client.post("/candidates", json=data)
    assert client.post("/candidates", json={**data, "email": "ANA@example.com"}).status_code == 409


def test_invalid_email_returns_422(client):
    assert client.post("/candidates", json={"name": "Ana", "email": "no-es-correo"}).status_code == 422


def test_filter_candidates_by_skill(client, demo_data):
    r = client.get("/candidates?skill=Postgres")
    assert r.status_code == 200
    assert all("postgresql" in c["skills"] for c in r.json())
    assert len(r.json()) >= 1


def test_deleting_job_deletes_its_applications(client, demo_data):
    r = client.delete("/jobs/1")
    assert r.json()["deleted_applications"] == 4
    assert client.get("/applications?job_id=1").json() == []
