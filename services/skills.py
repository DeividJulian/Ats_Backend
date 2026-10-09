"""Extracts skills from free text using a synonym catalog."""
import re

from services.nlp import normalize

# canonical skill -> synonyms it usually appears as in a resume
CATALOG: dict[str, list[str]] = {
    # Technology
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript"],
    "c#": ["c#", "csharp"],
    "c++": ["c++"],
    "php": ["php"],
    "sql": ["sql"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "react": ["react", "reactjs", "react.js"],
    "angular": ["angular"],
    "vue": ["vue", "vuejs", "vue.js"],
    "node.js": ["node.js", "nodejs", "node"],
    "django": ["django"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "spring boot": ["spring boot", "springboot", "spring"],
    "docker": ["docker"],
    "git": ["git", "github", "gitlab"],
    "linux": ["linux"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "api rest": ["api rest", "apis rest", "rest api", "restful", "servicios rest"],
    "machine learning": ["machine learning", "aprendizaje automatico", "ia", "inteligencia artificial"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "pruebas de software": ["pruebas de software", "testing", "qa", "pytest", "pruebas unitarias"],
    # Office, administration and finance
    "excel": ["excel", "hojas de calculo"],
    "word": ["word"],
    "power point": ["power point", "powerpoint"],
    "contabilidad": ["contabilidad", "contable", "contabilizacion"],
    "facturacion": ["facturacion", "facturas", "facturacion electronica"],
    "nomina": ["nomina", "liquidacion de nomina"],
    "tributaria": ["tributaria", "impuestos", "declaracion de renta", "dian", "iva"],
    "tesoreria": ["tesoreria", "conciliaciones bancarias", "conciliacion bancaria"],
    "siigo": ["siigo"],
    "sap": ["sap"],
    "inventarios": ["inventarios", "control de inventario", "gestion de inventarios"],
    "logistica": ["logistica", "cadena de suministro"],
    "compras": ["compras", "proveedores"],
    # Sales and marketing
    "ventas": ["ventas", "venta consultiva", "gestion comercial"],
    "atencion al cliente": ["atencion al cliente", "servicio al cliente", "servicio al usuario"],
    "negociacion": ["negociacion", "negociar"],
    "crm": ["crm", "hubspot", "salesforce"],
    "marketing digital": ["marketing digital", "mercadeo digital", "publicidad digital"],
    "redes sociales": ["redes sociales", "community manager", "social media"],
    "seo": ["seo", "posicionamiento web"],
    "diseno grafico": ["diseno grafico", "photoshop", "illustrator", "canva"],
    # Soft skills and management
    "gestion de proyectos": ["gestion de proyectos", "project management", "pmp"],
    "scrum": ["scrum", "metodologias agiles", "agile", "kanban"],
    "liderazgo": ["liderazgo", "liderar equipos", "lidere equipos", "manejo de equipos"],
    "trabajo en equipo": ["trabajo en equipo", "trabajo colaborativo"],
    "comunicacion": ["comunicacion asertiva", "comunicacion efectiva", "comunicacion"],
    "ingles": ["ingles", "english", "bilingue"],
    "analisis de datos": ["analisis de datos", "analitica de datos", "data analysis"],
}


def _compile() -> list[tuple[str, re.Pattern]]:
    patterns = []
    for canonical, synonyms in CATALOG.items():
        for s in synonyms:
            # The lookarounds keep "java" from matching inside "javascript" or "sql" inside "postgresql"
            pattern = re.compile(r"(?<![a-z0-9+#.])" + re.escape(normalize(s)) + r"(?![a-z0-9+#])")
            patterns.append((canonical, pattern))
    return patterns


_PATTERNS = _compile()

# Maps whatever the recruiter types to its canonical form ("Postgres" -> "postgresql")
_SYNONYM_TO_CANONICAL = {normalize(s): c for c, ss in CATALOG.items() for s in ss}


def extract_skills(text: str | None) -> list[str]:
    """Returns the catalog skills found in the text, deduplicated and sorted."""
    normalized = normalize(text)
    return sorted({canonical for canonical, pattern in _PATTERNS if pattern.search(normalized)})


def canonicalize_skills(skills: list[str] | None) -> list[str]:
    """Normalizes a hand-written list: lowercase, no accents and synonyms merged."""
    result = set()
    for skill in skills or []:
        clean = normalize(skill).strip()
        if clean:
            result.add(_SYNONYM_TO_CANONICAL.get(clean, clean))
    return sorted(result)


# Knowing the key skill strongly suggests knowing the listed ones ("django" -> "python")
IMPLIED_SKILLS: dict[str, list[str]] = {
    "django": ["python"],
    "fastapi": ["python", "api rest"],
    "flask": ["python"],
    "spring boot": ["java"],
    "react": ["javascript"],
    "vue": ["javascript"],
    "angular": ["typescript"],
    "typescript": ["javascript"],
    "node.js": ["javascript"],
    "postgresql": ["sql"],
    "mysql": ["sql"],
    "power bi": ["analisis de datos"],
    "tableau": ["analisis de datos"],
    "siigo": ["contabilidad"],
}


def infer_skills(skills: set[str] | list[str]) -> dict[str, str]:
    """Returns the skills implied by the given ones that are not already present, as {inferred: source}."""
    known = set(skills)
    inferred: dict[str, str] = {}
    pending = sorted(known)
    while pending:
        source = pending.pop()
        for implied in IMPLIED_SKILLS.get(source, []):
            if implied not in known and implied not in inferred:
                # Keep the original skill as the source, even through chains (angular -> typescript -> javascript)
                inferred[implied] = inferred.get(source, source)
                pending.append(implied)
    return inferred
