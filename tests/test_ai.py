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
