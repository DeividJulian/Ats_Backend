from services.nlp import normalize, tokenize
from services.profile import extract_education_level, extract_experience_years
from services.similarity import cosine_similarity
from services.skills import canonicalize_skills, extract_skills


def test_normalize_removes_accents_and_uppercase():
    assert normalize("Ingeniería de Sistemas") == "ingenieria de sistemas"


def test_tokenize_skips_stopwords_and_merges_plurals():
    assert tokenize("Los clientes de la empresa") == ["cliente", "empresa"]


def test_skills_do_not_confuse_java_with_javascript():
    assert extract_skills("Programo en JavaScript") == ["javascript"]
    assert "java" in extract_skills("Programo en Java y JavaScript")


def test_sql_is_not_detected_inside_postgresql():
    assert extract_skills("Uso PostgreSQL") == ["postgresql"]


def test_synonyms_are_merged():
    assert canonicalize_skills(["Postgres", " EXCEL ", "Inglés"]) == ["excel", "ingles", "postgresql"]


def test_experience_years():
    assert extract_experience_years("Tengo 25 años. Cuento con 5 años de experiencia en ventas") == 5
    assert extract_experience_years("Experiencia laboral de 3 años como contador") == 3
    assert extract_experience_years("Sin datos") == 0


def test_education_level_takes_the_highest():
    assert extract_education_level("Técnico en sistemas y Maestría en gestión") == "masters"
    assert extract_education_level("Ingeniero de sistemas") == "professional"
    assert extract_education_level("Me gusta correr") is None


def test_similarity_is_higher_for_similar_texts():
    similar = cosine_similarity("desarrollador python fastapi", "programador python con fastapi")
    different = cosine_similarity("desarrollador python fastapi", "vendedor de mostrador con experiencia")
    assert similar > different
    assert 0 <= different <= similar <= 1


def test_similarity_of_empty_text_is_zero():
    assert cosine_similarity("", "python") == 0.0


def test_analyze_text_endpoint(client):
    r = client.post("/nlp/analyze-text", json={"text": "Contador con 4 años de experiencia en Excel y Siigo"})
    assert r.status_code == 200
    body = r.json()
    assert body["experience_years"] == 4
    assert {"excel", "siigo"} <= set(body["skills"])


def test_similarity_endpoint(client):
    r = client.post("/nlp/similarity", json={"text_a": "ventas y negociación", "text_b": "ventas y negociación"})
    assert r.json()["similarity"] > 0.99
