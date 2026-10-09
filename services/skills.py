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
    "facturación": ["facturacion", "facturas", "facturacion electronica"],
    "nómina": ["nomina", "liquidacion de nomina"],
    "tributaria": ["tributaria", "impuestos", "declaracion de renta", "dian", "iva"],
    "tesorería": ["tesoreria", "conciliaciones bancarias", "conciliacion bancaria"],
    "siigo": ["siigo"],
    "sap": ["sap"],
    "inventarios": ["inventarios", "control de inventario", "gestion de inventarios"],
    "logística": ["logistica", "cadena de suministro"],
    "compras": ["compras", "proveedores"],
    # Sales and marketing
    "ventas": ["ventas", "venta consultiva", "gestion comercial"],
    "atención al cliente": ["atencion al cliente", "servicio al cliente", "servicio al usuario"],
    "negociación": ["negociacion", "negociar"],
    "crm": ["crm", "hubspot", "salesforce"],
    "marketing digital": ["marketing digital", "mercadeo digital", "publicidad digital"],
    "redes sociales": ["redes sociales", "community manager", "social media"],
    "seo": ["seo", "posicionamiento web"],
    "diseño gráfico": ["diseno grafico", "photoshop", "illustrator", "canva"],
    # Soft skills and management
    "gestión de proyectos": ["gestion de proyectos", "project management", "pmp"],
    "scrum": ["scrum", "metodologias agiles", "agile", "kanban"],
    "liderazgo": ["liderazgo", "liderar equipos", "lidere equipos", "manejo de equipos"],
    "trabajo en equipo": ["trabajo en equipo", "trabajo colaborativo"],
    "comunicación": ["comunicacion asertiva", "comunicacion efectiva", "comunicacion"],
    "inglés": ["ingles", "english", "bilingue"],
    "análisis de datos": ["analisis de datos", "analitica de datos", "data analysis"],
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


def sort_skills(skills) -> list[str]:
    """Alphabetical order ignoring accents, so "análisis" goes with the "a"."""
    return sorted(set(skills), key=normalize)


def extract_skills(text: str | None) -> list[str]:
    """Returns the catalog skills found in the text, deduplicated and sorted."""
    normalized = normalize(text)
    return sort_skills(canonical for canonical, pattern in _PATTERNS if pattern.search(normalized))


def canonicalize_skills(skills: list[str] | None) -> list[str]:
    """Normalizes a hand-written list: lowercase, no accents and synonyms merged."""
    result = set()
    for skill in skills or []:
        clean = normalize(skill).strip()
        if clean:
            result.add(_SYNONYM_TO_CANONICAL.get(clean, clean))
    return sort_skills(result)


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
    "power bi": ["análisis de datos"],
    "tableau": ["análisis de datos"],
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


# Professional area of each catalog skill, used to tailor summaries, interview questions and training
SKILL_AREAS: dict[str, list[str]] = {
    "technology": [
        "python", "java", "javascript", "typescript", "c#", "c++", "php", "sql", "postgresql", "mysql", "mongodb",
        "html", "css", "react", "angular", "vue", "node.js", "django", "fastapi", "flask", "spring boot", "docker",
        "git", "linux", "aws", "azure", "api rest", "machine learning", "power bi", "tableau",
        "pruebas de software", "análisis de datos",
    ],
    "administration": [
        "excel", "word", "power point", "contabilidad", "facturación", "nómina", "tributaria", "tesorería", "siigo",
        "sap", "inventarios", "logística", "compras",
    ],
    "sales": [
        "ventas", "atención al cliente", "negociación", "crm", "marketing digital", "redes sociales", "seo",
        "diseño gráfico",
    ],
    "soft_skills": ["gestión de proyectos", "scrum", "liderazgo", "trabajo en equipo", "comunicación", "inglés"],
}

_AREA_BY_SKILL = {skill: area for area, skills in SKILL_AREAS.items() for skill in skills}


def skill_area(skill: str) -> str:
    return _AREA_BY_SKILL.get(skill, "general")
