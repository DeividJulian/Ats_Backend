"""Procesamiento básico de lenguaje natural en español (sin librerías externas)."""
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


def quitar_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def normalizar(texto: str | None) -> str:
    """Minúsculas y sin acentos. 'Ingeniería' -> 'ingenieria'."""
    return quitar_acentos((texto or "").lower())


def _raiz(palabra: str) -> str:
    """Stemming muy ligero: unifica plurales ('bases' -> 'base', 'clientes' -> 'cliente')."""
    if len(palabra) > 4 and palabra.endswith("es"):
        return palabra[:-1]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def tokenizar(texto: str | None) -> list[str]:
    """Convierte un texto en una lista de términos relevantes (sin stopwords ni números sueltos)."""
    tokens = []
    for crudo in re.findall(r"[a-z0-9+#.]+", normalizar(texto)):
        palabra = crudo.strip(".")
        if len(palabra) < 2 or palabra.isdigit() or palabra in STOPWORDS:
            continue
        tokens.append(_raiz(palabra))
    return tokens
