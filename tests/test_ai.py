from tests.conftest import make_pdf
from services.scoring import compute_match
from services.skills import infer_skills


def test_related_skills_are_inferred_through_chains():
    assert infer_skills({"angular", "postgresql"}) == {"typescript": "angular", "javascript": "angular", "sql": "postgresql"}


def test_inferred_skill_gets_partial_credit():
    job = {"title": "Dev", "description": "web", "required_skills": ["sql"]}
    proven = compute_match(job, {"resume_text": "dev", "skills": ["sql"]})
    inferred = compute_match(job, {"resume_text": "dev", "skills": ["postgresql"]})
    assert inferred["inferred_skills"] == {"sql": "postgresql"}
    assert inferred["missing_skills"] == []
    assert inferred["breakdown"]["skills"] == 75.0
    assert proven["breakdown"]["skills"] == 100.0


def test_recommended_jobs_exclude_applied_and_closed(client, demo_data):
    # Camila (1) applied to job 1; job 2 gets closed, so only job 3 can be recommended
    client.patch("/jobs/2/status", json={"status": "closed"})
    jobs = client.get("/candidates/1/recommended-jobs").json()
    assert [j["job_id"] for j in jobs] == [3]


def test_recommended_jobs_are_sorted_by_score(client, demo_data):
    client.post("/jobs", json={
        "title": "Desarrollador Python", "description": "APIs REST con Python y FastAPI", "requirements": "Python, Docker",
    })
    jobs = client.get("/candidates/1/recommended-jobs").json()
    assert jobs[0]["title"] == "Desarrollador Python"
    assert [j["score"] for j in jobs] == sorted((j["score"] for j in jobs), reverse=True)
    assert client.get("/candidates/99/recommended-jobs").status_code == 404


RESUME = "HOJA DE VIDA\nLUIS MORA DIAZ\nCel +57 310 555 1234 - luis.mora@example.com\nContador Publico con 6 anos de experiencia en contabilidad, Siigo y Excel"


def test_contact_data_is_extracted():
    from services.contact import extract_email, extract_name, extract_phone

    assert extract_name(RESUME) == "Luis Mora Diaz"
    assert extract_email(RESUME) == "luis.mora@example.com"
    assert extract_phone(RESUME) == "+57 310 555 1234"
    assert extract_phone("Trabaje de 2018 a 2023") is None
    assert extract_name("Perfil profesional\nDesarrollador", "ana_ruiz@mail.com") == "Ana Ruiz"


def test_analyze_resume_does_not_save(client):
    r = client.post("/nlp/analyze-resume", files={"file": ("cv.pdf", make_pdf(RESUME), "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Luis Mora Diaz" and body["email"] == "luis.mora@example.com"
    assert {"contabilidad", "siigo", "excel"} <= set(body["skills"])
    assert body["experience_years"] == 6 and body["education_level"] == "professional"
    assert client.get("/candidates").json() == []


def test_create_candidate_from_resume(client):
    r = client.post("/candidates/from-resume", files={"file": ("cv.pdf", make_pdf(RESUME), "application/pdf")})
    assert r.status_code == 201
    assert r.json()["name"] == "Luis Mora Diaz"
    assert r.json()["phone"] == "+57 310 555 1234"
    again = client.post("/candidates/from-resume", files={"file": ("cv.pdf", make_pdf(RESUME), "application/pdf")})
    assert again.status_code == 409


def test_resume_without_email_returns_422(client):
    pdf = make_pdf("Luis Mora\nContador con 6 anos de experiencia en Excel")
    r = client.post("/candidates/from-resume", files={"file": ("cv.pdf", pdf, "application/pdf")})
    assert r.status_code == 422
    assert "correo" in r.json()["detail"]


def test_candidate_insights(client, demo_data):
    r = client.get("/candidates/1/insights")
    assert r.status_code == 200
    body = r.json()
    assert body["main_area"] == "technology"
    assert "profesional" in body["summary"] and "3 años" in body["summary"]
    assert "python" in body["skills_by_area"]["technology"]
    # Camila is a developer: the open accounting and sales jobs ask for skills she lacks
    to_develop = {s["skill"] for s in body["skills_to_develop"]}
    assert to_develop and "python" not in to_develop
    assert all(s["suggestion"] for s in body["skills_to_develop"])
    assert client.get("/candidates/99/insights").status_code == 404


def test_interview_guide_covers_strengths_and_gaps(client, demo_data):
    # Application 3: Valentina (Java developer) for the Python job, low fit
    r = client.get("/applications/3/interview-guide")
    assert r.status_code == 200
    guide = r.json()
    types = {q["type"] for q in guide["questions"]}
    assert {"gap", "area", "motivation"} <= types
    assert guide["gaps"] and len(guide["training_for_gaps"]) == len(guide["gaps"])
    assert guide["classification"] == "low" and "bajo" in guide["focus"].lower()
    assert any(q["type"] == "strength" for q in client.get("/applications/1/interview-guide").json()["questions"])
    assert client.get("/applications/99/interview-guide").status_code == 404
