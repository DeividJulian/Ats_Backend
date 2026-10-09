"""Text similarity with TF-IDF and cosine, implemented from scratch."""
import math
from collections import Counter

from services.nlp import tokenize


def _idf(documents_tokens: list[list[str]]) -> dict[str, float]:
    n = len(documents_tokens)
    df = Counter()
    for tokens in documents_tokens:
        df.update(set(tokens))
    # Smoothed IDF: never zero and never divides by zero
    return {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {t: (c / total) * idf.get(t, 1.0) for t, c in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(t, 0.0) for t, value in a.items())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def cosine_similarity(text_a: str, text_b: str, corpus: list[str] | None = None) -> float:
    """Returns a value between 0 and 1. The corpus (other texts in the system) improves each term's weight."""
    tokens_a, tokens_b = tokenize(text_a), tokenize(text_b)
    documents = [tokens_a, tokens_b] + [tokenize(t) for t in (corpus or [])]
    idf = _idf(documents)
    return round(_cosine(_tfidf_vector(tokens_a, idf), _tfidf_vector(tokens_b, idf)), 4)
