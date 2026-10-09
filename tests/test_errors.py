def test_validation_error_has_uniform_format(client):
    r = client.post("/candidates", json={"name": "A", "email": "malo"})
    assert r.status_code == 422
    body = r.json()
    assert list(body) == ["detail"] and isinstance(body["detail"], str)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_error_messages_are_in_spanish(client):
    r = client.post("/candidates", json={"name": "A", "email": "malo"})
    assert r.json()["detail"] == (
        "name: debe tener al menos 2 caracteres; email: no es un correo electrónico válido"
    )
    assert client.get("/no-existe").json() == {"detail": "Recurso no encontrado"}
