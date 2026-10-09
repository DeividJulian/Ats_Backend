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
