JOB = {
    "titulo": "Analista de datos",
    "descripcion": "Analizar información comercial y construir tableros para la gerencia.",
    "requisitos": "Excel, SQL y Power BI",
    "experiencia_minima_anios": 2,
}


def test_job_infers_skills_from_text(client):
    r = client.post("/vacantes", json=JOB)
    assert r.status_code == 201
    assert {"excel", "sql", "power bi"} <= set(r.json()["habilidades_requeridas"])


def test_job_keeps_hand_written_skills(client):
    r = client.post("/vacantes", json={**JOB, "habilidades_requeridas": ["Postgres"]})
    assert r.json()["habilidades_requeridas"] == ["postgresql"]


def test_invalid_job_returns_422(client):
    r = client.post("/vacantes", json={**JOB, "titulo": "A", "experiencia_minima_anios": 99})
    assert r.status_code == 422


def test_missing_job_returns_404(client):
    assert client.get("/vacantes/999").status_code == 404


def test_close_job(client):
    job = client.post("/vacantes", json=JOB).json()
    r = client.patch(f"/vacantes/{job['id']}/estado", json={"estado": "cerrada"})
    assert r.json()["estado"] == "cerrada"
    assert len(client.get("/vacantes?estado=abierta").json()) == 0


def test_candidate_profile_is_extracted_from_resume(client):
    r = client.post(
        "/candidatos",
        json={
            "nombre": "Ana Ruiz",
            "email": "ana@example.com",
            "cv_texto": "Ingeniera de sistemas con 4 años de experiencia en Python y Docker",
        },
    )
    assert r.status_code == 201
    candidate = r.json()
    assert {"python", "docker"} <= set(candidate["habilidades"])
    assert candidate["anios_experiencia"] == 4
    assert candidate["nivel_educacion"] == "profesional"


def test_manual_data_takes_priority(client):
    r = client.post(
        "/candidatos",
        json={"nombre": "Ana Ruiz", "email": "ana@example.com", "cv_texto": "5 años de experiencia", "anios_experiencia": 1},
    )
    assert r.json()["anios_experiencia"] == 1


def test_duplicate_email_returns_409(client):
    data = {"nombre": "Ana Ruiz", "email": "ana@example.com"}
    client.post("/candidatos", json=data)
    assert client.post("/candidatos", json={**data, "email": "ANA@example.com"}).status_code == 409


def test_invalid_email_returns_422(client):
    assert client.post("/candidatos", json={"nombre": "Ana", "email": "no-es-correo"}).status_code == 422


def test_filter_candidates_by_skill(client, demo_data):
    r = client.get("/candidatos?habilidad=Postgres")
    assert r.status_code == 200
    assert all("postgresql" in c["habilidades"] for c in r.json())
    assert len(r.json()) >= 1


def test_deleting_job_deletes_its_applications(client, demo_data):
    r = client.delete("/vacantes/1")
    assert r.json()["postulaciones_eliminadas"] == 4
    assert client.get("/postulaciones?vacante_id=1").json() == []
