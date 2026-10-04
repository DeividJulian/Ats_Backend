"""Extracción de habilidades a partir de texto libre usando un catálogo de sinónimos."""
import re

from services.nlp import normalizar

# habilidad canónica -> sinónimos con los que suele aparecer en una hoja de vida
CATALOGO: dict[str, list[str]] = {
    # Tecnología
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
    # Oficina, administración y finanzas
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
    # Comercial y marketing
    "ventas": ["ventas", "venta consultiva", "gestion comercial"],
    "atencion al cliente": ["atencion al cliente", "servicio al cliente", "servicio al usuario"],
    "negociacion": ["negociacion", "negociar"],
    "crm": ["crm", "hubspot", "salesforce"],
    "marketing digital": ["marketing digital", "mercadeo digital", "publicidad digital"],
    "redes sociales": ["redes sociales", "community manager", "social media"],
    "seo": ["seo", "posicionamiento web"],
    "diseno grafico": ["diseno grafico", "photoshop", "illustrator", "canva"],
    # Habilidades blandas y gestión
    "gestion de proyectos": ["gestion de proyectos", "project management", "pmp"],
    "scrum": ["scrum", "metodologias agiles", "agile", "kanban"],
    "liderazgo": ["liderazgo", "liderar equipos", "lidere equipos", "manejo de equipos"],
    "trabajo en equipo": ["trabajo en equipo", "trabajo colaborativo"],
    "comunicacion": ["comunicacion asertiva", "comunicacion efectiva", "comunicacion"],
    "ingles": ["ingles", "english", "bilingue"],
    "analisis de datos": ["analisis de datos", "analitica de datos", "data analysis"],
}


def _compilar() -> list[tuple[str, re.Pattern]]:
    patrones = []
    for canonica, sinonimos in CATALOGO.items():
        for s in sinonimos:
            # El lookaround evita que "java" coincida dentro de "javascript" o "sql" dentro de "postgresql"
            patron = re.compile(r"(?<![a-z0-9+#.])" + re.escape(normalizar(s)) + r"(?![a-z0-9+#])")
            patrones.append((canonica, patron))
    return patrones


_PATRONES = _compilar()

# Para convertir lo que escriba el reclutador a la forma canónica ("Postgres" -> "postgresql")
_SINONIMO_A_CANONICA = {normalizar(s): c for c, ss in CATALOGO.items() for s in ss}


def extraer_habilidades(texto: str | None) -> list[str]:
    """Devuelve las habilidades del catálogo que aparecen en el texto, sin repetir y ordenadas."""
    normal = normalizar(texto)
    return sorted({canonica for canonica, patron in _PATRONES if patron.search(normal)})


def canonizar_habilidades(habilidades: list[str] | None) -> list[str]:
    """Normaliza una lista escrita a mano: minúsculas, sin acentos y con sinónimos unificados."""
    resultado = set()
    for h in habilidades or []:
        limpia = normalizar(h).strip()
        if limpia:
            resultado.add(_SINONIMO_A_CANONICA.get(limpia, limpia))
    return sorted(resultado)
