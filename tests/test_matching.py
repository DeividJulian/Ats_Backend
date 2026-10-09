from tests.conftest import make_pdf


def test_ranking_is_sorted_by_score(client, demo_data):
    ranking = client.get("/jobs/1/ranking").json()
    scores = [r["score"] for r in ranking]
    assert scores == sorted(scores, reverse=True)
    assert [r["position"] for r in ranking] == list(range(1, len(ranking) + 1))
    assert ranking[0]["name"] == "Camila Ortega"


def test_ideal_candidate_gets_high_score(client, demo_data):
    ranking = client.get("/jobs/2/ranking").json()
    assert ranking[0]["name"] == "Andrés Molina"
    assert ranking[0]["classification"] == "high"


def test_score_includes_explanation(client, demo_data):
    application = client.get("/applications/1").json()
    assert 0 <= application["score"] <= 100
    assert application["details"]["explanation"]
    assert "skills" in application["details"]["breakdown"]


def test_applying_computes_score(client, demo_data):
    r = client.post("/applications", json={"job_id": 3, "candidate_id": 1})
    assert r.status_code == 201
    assert r.json()["status"] == "new"
    assert 0 <= r.json()["score"] <= 100


def test_cannot_apply_twice(client, demo_data):
    r = client.post("/applications", json={"job_id": 1, "candidate_id": 1})
    assert r.status_code == 409


def test_closed_job_rejects_applications(client, demo_data):
    client.patch("/jobs/3/status", json={"status": "closed"})
    r = client.post("/applications", json={"job_id": 3, "candidate_id": 1})
    assert r.status_code == 409


def test_applying_with_missing_ids_returns_404(client, demo_data):
    assert client.post("/applications", json={"job_id": 99, "candidate_id": 1}).status_code == 404


def test_suggestions_exclude_applicants(client, demo_data):
    applicants = {r["candidate_id"] for r in client.get("/jobs/1/ranking").json()}
    suggestions = client.get("/jobs/1/suggested-candidates?limit=20").json()
    assert suggestions and not applicants & {s["candidate_id"] for s in suggestions}
    scores = [s["score"] for s in suggestions]
    assert scores == sorted(scores, reverse=True)


def test_recalculate_after_editing_job(client, demo_data):
    before = client.get("/applications/1").json()["score"]
    job = client.get("/jobs/1").json()
    job["required_skills"] = ["python"]
    job["requirements"] = "Python"
    client.put("/jobs/1", json=job)
    r = client.post("/jobs/1/recalculate-ranking")
    assert r.json()["updated_applications"] == 4
    after = client.get("/applications/1").json()
    assert after["details"]["missing_skills"] == []
    assert after["score"] != before


def test_valid_pipeline_transitions(client, demo_data):
    assert client.patch("/applications/3/status", json={"status": "shortlisted"}).status_code == 200
    assert client.patch("/applications/3/status", json={"status": "interview"}).status_code == 200


def test_invalid_transition_returns_409(client, demo_data):
    r = client.patch("/applications/3/status", json={"status": "hired"})
    assert r.status_code == 409
    assert "preseleccionado" in r.json()["detail"]


def test_final_status_cannot_change(client, demo_data):
    r = client.patch("/applications/4/status", json={"status": "new"})
    assert r.status_code == 409
    assert "final" in r.json()["detail"]


def test_uploading_pdf_resume_updates_profile(client):
    candidate = client.post("/candidates", json={"name": "Luis Mora", "email": "luis@example.com"}).json()
    pdf = make_pdf("Contador Publico con 6 anos de experiencia en contabilidad y Excel")
    r = client.post(f"/candidates/{candidate['id']}/resume", files={"file": ("cv.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    assert {"contabilidad", "excel"} <= set(r.json()["skills"])
    assert r.json()["experience_years"] == 6


def test_uploading_non_pdf_returns_422(client):
    candidate = client.post("/candidates", json={"name": "Luis Mora", "email": "luis@example.com"}).json()
    r = client.post(f"/candidates/{candidate['id']}/resume", files={"file": ("cv.txt", b"hola", "text/plain")})
    assert r.status_code == 422


def test_uploading_resume_for_missing_candidate_returns_404(client):
    r = client.post("/candidates/99/resume", files={"file": ("cv.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 404
