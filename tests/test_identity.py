"""A resume is accepted only when it belongs to the person whose profile receives it."""
import pytest

from database import SessionLocal
from models.candidate import Candidate
from services.identity import name_words, resume_mismatch, same_person
from tests.conftest import make_pdf, register

DEIVID = ("Deivid Julian Alvarado Moran", "deivid@gmail.com")
OWN_CV = "DEIVID JULIÁN ALVARADO MORÁN\nIngeniero de sistemas\ndeivid@gmail.com\nPython, FastAPI y PostgreSQL. 6 años de experiencia."
CARLOS_CV = "Carlos Andrés Ortega Benavides\nContador Público\ncarlos.ortega@example.com\nContabilidad, Siigo y Excel avanzado."


def test_name_words_ignore_accents_case_and_connectors():
    assert name_words("José de la Peña") == {"jose", "pena"}
    assert name_words("DEIVID JULIÁN") == {"deivid", "julian"}


@pytest.mark.parametrize("a, b, expected", [
    ("Deivid Julian Alvarado Moran", "DEIVID JULIÁN ALVARADO MORÁN", True),
    ("Deivid Julian Alvarado Moran", "Deivid Alvarado", True),          # first name and a surname
    ("Camila Ortega", "Carlos Andrés Ortega Benavides", False),         # only the surname in common
    ("Deivid Julian Alvarado Moran", "Carlos Andrés Ortega", False),
    ("Madonna", "Madonna Ciccone", True),
    ("", "Carlos Ortega", False),
])
def test_same_person(a, b, expected):
    assert same_person(a, b) is expected


def test_resume_mismatch_rules():
    assert resume_mismatch(*DEIVID, OWN_CV) is None
    reason = resume_mismatch(*DEIVID, CARLOS_CV)
    assert "Carlos Andrés Ortega Benavides" in reason and "Deivid Julian Alvarado Moran" in reason
    # Their own email is enough, even if the name line is written differently
    assert resume_mismatch("Deivid Alvarado", "carlos.ortega@example.com", CARLOS_CV) is None
    # No name line, but the name appears near the top
    assert resume_mismatch(*DEIVID, "Perfil profesional de Deivid Alvarado, desarrollador backend.") is None
    # No name line and someone else's email
    assert "otro@mail.com" in resume_mismatch(*DEIVID, "Perfil: desarrollador backend.\notro@mail.com")
    # Nothing identifies anybody: accepted
    assert resume_mismatch(*DEIVID, "Experiencia en Python y SQL durante 3 años.") is None
    assert resume_mismatch(*DEIVID, "") is None


@pytest.fixture
def deivid():
    return register(*DEIVID)


def test_candidate_cannot_upload_someone_elses_pdf(deivid):
    r = deivid.post("/me/resume", files={"file": ("cv.pdf", make_pdf(CARLOS_CV), "application/pdf")})
    assert r.status_code == 422
    detail = r.json()["detail"]
    # The reason is Carlos's name or his email (the tiny test PDF may lose the accent of "Andrés")
    assert ("Carlos" in detail or "carlos.ortega@example.com" in detail) and "Sube tu propia hoja de vida" in detail
    profile = deivid.get("/me/profile").json()
    assert profile["resume_text"] == "" and profile["skills"] == []


def test_candidate_uploads_their_own_pdf(deivid):
    r = deivid.post("/me/resume", files={"file": ("cv.pdf", make_pdf(OWN_CV), "application/pdf")})
    assert r.status_code == 200 and "python" in r.json()["skills"]


def test_candidate_cannot_paste_someone_elses_resume(deivid):
    body = {"name": DEIVID[0], "phone": None, "resume_text": CARLOS_CV, "skills": []}
    r = deivid.put("/me/profile", json=body)
    assert r.status_code == 422
    assert deivid.get("/me/profile").json()["resume_text"] == ""
    assert deivid.put("/me/profile", json={**body, "resume_text": OWN_CV}).status_code == 200
    # Saving other fields keeps working with the resume already there
    assert deivid.put("/me/profile", json={**body, "resume_text": OWN_CV, "phone": "3001112233"}).status_code == 200


def test_recruiter_cannot_attach_a_resume_to_the_wrong_candidate(client, demo_data):
    camila = next(c for c in client.get("/candidates").json() if c["name"] == "Camila Ortega")
    before = camila["resume_text"]
    r = client.post(f"/candidates/{camila['id']}/resume", files={"file": ("cv.pdf", make_pdf(CARLOS_CV), "application/pdf")})
    assert r.status_code == 422 and "candidato correcto" in r.json()["detail"]
    with SessionLocal() as db:
        assert db.get(Candidate, camila["id"]).resume_text == before


def test_recruiter_edit_checks_the_pasted_resume(client, demo_data):
    camila = next(c for c in client.get("/candidates").json() if c["name"] == "Camila Ortega")
    body = {"name": camila["name"], "email": camila["email"], "phone": None, "resume_text": CARLOS_CV, "skills": []}
    assert client.put(f"/candidates/{camila['id']}", json=body).status_code == 422
    # Unchanged resume text is not checked again, so other edits keep working
    keep = {**body, "resume_text": camila["resume_text"], "phone": "3001112233"}
    assert client.put(f"/candidates/{camila['id']}", json=keep).status_code == 200
