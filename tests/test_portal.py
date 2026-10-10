import pytest
from fastapi.testclient import TestClient

from main import app
from services.seed import DEMO_PASSWORD
from tests.conftest import login, make_pdf


@pytest.fixture
def camila(demo_data):
    """Demo candidate: Camila Ortega (candidate 1), already applied to job 1."""
    return login("camila.ortega@example.com", DEMO_PASSWORD)


@pytest.fixture
def newcomer(anon):
    r = anon.post("/auth/register", json={"name": "Juan Pérez", "email": "juan@mail.com", "password": "Clave1234"})
    return TestClient(app, headers={"Authorization": f"Bearer {r.json()['access_token']}"})


def test_my_applications_hide_the_score(camila):
    apps = camila.get("/me/applications").json()
    assert [a["job_title"] for a in apps] == ["Desarrollador Backend Python Junior"]
    assert apps[0]["status"] == "interview"
    assert "score" not in apps[0] and "missing_skills" in apps[0]


def test_apply_and_withdraw(camila, client):
    r = camila.post("/me/applications", json={"job_id": 3})
    assert r.status_code == 201 and r.json()["status"] == "new"
    assert camila.post("/me/applications", json={"job_id": 3}).status_code == 409
    # The recruiters see the new application, with its score
    ranking = client.get("/jobs/3/ranking").json()
    assert "Camila Ortega" in [x["name"] for x in ranking]
    assert camila.delete(f"/me/applications/{r.json()['id']}").status_code == 200
    assert len(camila.get("/me/applications").json()) == 1


def test_cannot_touch_someone_elses_application(camila):
    # Application 2 belongs to Sebastián Rojas
    assert camila.delete("/me/applications/2").status_code == 404


def test_cannot_withdraw_a_hire(camila, client):
    for status in ("offer", "hired"):
        client.patch("/applications/1/status", json={"status": status})
    assert camila.delete("/me/applications/1").status_code == 409


def test_cannot_apply_to_closed_job(camila, client):
    client.patch("/jobs/2/status", json={"status": "closed"})
    assert camila.post("/me/applications", json={"job_id": 2}).status_code == 409


def test_update_profile_extracts_from_resume(newcomer):
    r = newcomer.put("/me/profile", json={
        "name": "Juan Pérez Gil", "phone": "3001234567",
        "resume_text": "Contador público con 4 años de experiencia en Siigo y Excel",
    })
    assert r.status_code == 200
    profile = r.json()
    assert {"siigo", "excel"} <= set(profile["skills"])
    assert profile["experience_years"] == 4 and profile["education_level"] == "professional"
    assert newcomer.get("/auth/me").json()["name"] == "Juan Pérez Gil"
    assert profile["email"] == "juan@mail.com"


def test_upload_my_resume(newcomer):
    pdf = make_pdf("Desarrollador con 3 anos de experiencia en Python, Django y Docker")
    r = newcomer.post("/me/resume", files={"file": ("cv.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    assert {"python", "django", "docker"} <= set(r.json()["skills"])
    bad = newcomer.post("/me/resume", files={"file": ("cv.txt", b"hola", "text/plain")})
    assert bad.status_code == 422


def test_my_recommendations_and_insights(demo_data, newcomer):
    newcomer.put("/me/profile", json={"name": "Juan Pérez", "resume_text": "Contador con 5 años de experiencia en contabilidad, Siigo, Excel y nómina"})
    jobs = newcomer.get("/me/recommended-jobs").json()
    assert jobs[0]["title"] == "Auxiliar Contable"
    insights = newcomer.get("/me/insights").json()
    assert insights["main_area"] == "administration" and insights["summary"]
