"""Basic Spanish natural language processing (no external libraries)."""
import re
import unicodedata

STOPWORDS = {
    "a", "al", "algo", "ante", "antes", "aqui", "asi", "aun", "bajo", "cada", "como", "con", "contra",
    "cual", "cuando", "de", "del", "desde", "donde", "durante", "e", "el", "ella", "ellos", "en", "entre",
    "era", "es", "esa", "ese", "eso", "esta", "estar", "este", "esto", "fue", "ha", "han", "hasta", "hay",
    "la", "las", "le", "les", "lo", "los", "mas", "me", "mi", "mis", "mucho", "muy", "ni", "no", "nos",
    "nuestro", "o", "otro", "para", "pero", "por", "porque", "que", "se", "ser", "si", "sin", "sobre",
    "son", "su", "sus", "tambien", "tan", "te", "tener", "tiene", "todo", "tu", "un", "una", "uno", "unos",
    "y", "ya", "yo", "the", "and", "of", "to", "in", "for", "with", "on", "at", "by", "an",
}


def remove_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def normalize(text: str | None) -> str:
    """Lowercase without accents. 'Ingeniería' -> 'ingenieria'."""
    return remove_accents((text or "").lower())


def _stem(word: str) -> str:
    """Very light stemming: merges plurals ('bases' -> 'base', 'clientes' -> 'cliente')."""
    if len(word) > 4 and word.endswith("es"):
        return word[:-1]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def tokenize(text: str | None) -> list[str]:
    """Turns a text into a list of relevant terms (no stopwords or standalone numbers)."""
    tokens = []
    for raw in re.findall(r"[a-z0-9+#.]+", normalize(text)):
        word = raw.strip(".")
        if len(word) < 2 or word.isdigit() or word in STOPWORDS:
            continue
        tokens.append(_stem(word))
    return tokens
