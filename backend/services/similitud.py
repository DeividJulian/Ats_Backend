"""Similitud entre textos con TF-IDF y coseno, implementada desde cero."""
import math
from collections import Counter

from services.nlp import tokenizar


def _idf(documentos_tokens: list[list[str]]) -> dict[str, float]:
    n = len(documentos_tokens)
    df = Counter()
    for tokens in documentos_tokens:
        df.update(set(tokens))
    # IDF suavizado: nunca es cero ni divide entre cero
    return {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}


def _vector_tfidf(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    conteo = Counter(tokens)
    total = len(tokens)
    return {t: (c / total) * idf.get(t, 1.0) for t, c in conteo.items()}


def _coseno(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    producto = sum(valor * b.get(t, 0.0) for t, valor in a.items())
    norma_a = math.sqrt(sum(v * v for v in a.values()))
    norma_b = math.sqrt(sum(v * v for v in b.values()))
    return producto / (norma_a * norma_b) if norma_a and norma_b else 0.0


def similitud_coseno(texto_a: str, texto_b: str, corpus: list[str] | None = None) -> float:
    """Devuelve un valor entre 0 y 1. El corpus (otros textos del sistema) mejora el peso de cada término."""
    tokens_a, tokens_b = tokenizar(texto_a), tokenizar(texto_b)
    documentos = [tokens_a, tokens_b] + [tokenizar(t) for t in (corpus or [])]
    idf = _idf(documentos)
    return round(_coseno(_vector_tfidf(tokens_a, idf), _vector_tfidf(tokens_b, idf)), 4)
