from tests.conftest import make_pdf


def test_ranking_is_sorted_by_score(client, demo_data):
    ranking = client.get("/vacantes/1/ranking").json()
    scores = [r["score"] for r in ranking]
    assert scores == sorted(scores, reverse=True)
    assert [r["posicion"] for r in ranking] == list(range(1, len(ranking) + 1))
    assert ranking[0]["nombre"] == "Camila Ortega"


def test_ideal_candidate_gets_high_score(client, demo_data):
    ranking = client.get("/vacantes/2/ranking").json()
    assert ranking[0]["nombre"] == "Andrés Molina"
    assert ranking[0]["clasificacion"] == "alto"


def test_score_includes_explanation(client, demo_data):
    application = client.get("/postulaciones/1").json()
    assert 0 <= application["score"] <= 100
    assert application["detalle"]["explicacion"]
    assert "habilidades" in application["detalle"]["desglose"]


def test_applying_computes_score(client, demo_data):
    r = client.post("/postulaciones", json={"vacante_id": 3, "candidato_id": 1})
    assert r.status_code == 201
    assert r.json()["estado"] == "nuevo"
    assert 0 <= r.json()["score"] <= 100


def test_cannot_apply_twice(client, demo_data):
    r = client.post("/postulaciones", json={"vacante_id": 1, "candidato_id": 1})
    assert r.status_code == 409


def test_closed_job_rejects_applications(client, demo_data):
    client.patch("/vacantes/3/estado", json={"estado": "cerrada"})
    r = client.post("/postulaciones", json={"vacante_id": 3, "candidato_id": 1})
    assert r.status_code == 409


def test_applying_with_missing_ids_returns_404(client, demo_data):
    assert client.post("/postulaciones", json={"vacante_id": 99, "candidato_id": 1}).status_code == 404


def test_suggestions_exclude_applicants(client, demo_data):
    applicants = {r["candidato_id"] for r in client.get("/vacantes/1/ranking").json()}
    suggestions = client.get("/vacantes/1/candidatos-sugeridos?limite=20").json()
    assert suggestions and not applicants & {s["candidato_id"] for s in suggestions}
    scores = [s["score"] for s in suggestions]
    assert scores == sorted(scores, reverse=True)


def test_recalculate_after_editing_job(client, demo_data):
    before = client.get("/postulaciones/1").json()["score"]
    job = client.get("/vacantes/1").json()
    job["habilidades_requeridas"] = ["python"]
    job["requisitos"] = "Python"
    client.put("/vacantes/1", json=job)
    r = client.post("/vacantes/1/recalcular-ranking")
    assert r.json()["postulaciones_actualizadas"] == 4
    after = client.get("/postulaciones/1").json()
    assert after["detalle"]["habilidades_faltantes"] == []
    assert after["score"] != before


def test_valid_pipeline_transitions(client, demo_data):
    assert client.patch("/postulaciones/3/estado", json={"estado": "preseleccionado"}).status_code == 200
    assert client.patch("/postulaciones/3/estado", json={"estado": "entrevista"}).status_code == 200


def test_invalid_transition_returns_409(client, demo_data):
    r = client.patch("/postulaciones/3/estado", json={"estado": "contratado"})
    assert r.status_code == 409
    assert "preseleccionado" in r.json()["detail"]


def test_final_status_cannot_change(client, demo_data):
    r = client.patch("/postulaciones/4/estado", json={"estado": "nuevo"})
    assert r.status_code == 409
    assert "final" in r.json()["detail"]


def test_uploading_pdf_resume_updates_profile(client):
    candidate = client.post("/candidatos", json={"nombre": "Luis Mora", "email": "luis@example.com"}).json()
    pdf = make_pdf("Contador Publico con 6 anos de experiencia en contabilidad y Excel")
    r = client.post(f"/candidatos/{candidate['id']}/cv", files={"archivo": ("cv.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    assert {"contabilidad", "excel"} <= set(r.json()["habilidades"])
    assert r.json()["anios_experiencia"] == 6


def test_uploading_non_pdf_returns_422(client):
    candidate = client.post("/candidatos", json={"nombre": "Luis Mora", "email": "luis@example.com"}).json()
    r = client.post(f"/candidatos/{candidate['id']}/cv", files={"archivo": ("cv.txt", b"hola", "text/plain")})
    assert r.status_code == 422


def test_uploading_resume_for_missing_candidate_returns_404(client):
    r = client.post("/candidatos/99/cv", files={"archivo": ("cv.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 404
