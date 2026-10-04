def test_statistics_with_demo_data(client, demo_data):
    stats = client.get("/estadisticas").json()
    assert stats["totales"] == {"vacantes": 3, "vacantes_abiertas": 3, "candidatos": 9, "postulaciones": 10}
    assert sum(stats["embudo"].values()) == 10
    assert len(stats["por_vacante"]) == 3
    assert stats["habilidades_mas_demandadas"]


def test_statistics_without_data(client):
    stats = client.get("/estadisticas").json()
    assert stats["totales"]["postulaciones"] == 0
    assert stats["tasa_contratacion_pct"] == 0.0


def test_hiring_rate(client, demo_data):
    for status in ("preseleccionado", "entrevista", "oferta", "contratado"):
        client.patch("/postulaciones/3/estado", json={"estado": status})
    assert client.get("/estadisticas").json()["tasa_contratacion_pct"] == 10.0


def test_seed_does_not_overwrite_without_reset(client, demo_data):
    assert client.post("/seed").status_code == 409
    assert client.post("/seed?reiniciar=true").status_code == 200
    assert len(client.get("/candidatos").json()) == demo_data["candidatos"]
