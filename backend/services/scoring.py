"""Cálculo explicable del porcentaje de ajuste (match score) entre una vacante y un candidato."""
from services.perfil import nivel_a_numero
from services.similitud import similitud_coseno

PESOS = {"habilidades": 0.50, "texto": 0.20, "experiencia": 0.20, "educacion": 0.10}

# Los cosenos entre textos reales rara vez superan 0.30, así que se escala para que 0.30 cuente como ajuste total
COSENO_REFERENCIA = 0.30


def clasificar(score: float) -> str:
    if score >= 75:
        return "alto"
    if score >= 50:
        return "medio"
    return "bajo"


def calcular_match(vacante: dict, candidato: dict, corpus: list[str] | None = None) -> dict:
    """
    vacante: titulo, descripcion, requisitos, habilidades_requeridas, experiencia_minima_anios, nivel_educacion_minimo
    candidato: cv_texto, habilidades, anios_experiencia, nivel_educacion
    Solo se evalúa lo que la vacante realmente exige: los criterios sin requisito se omiten y los pesos se reparten.
    """
    explicacion = []
    componentes = {}  # criterio -> puntaje de 0 a 1

    requeridas = set(vacante.get("habilidades_requeridas") or [])
    del_candidato = set(candidato.get("habilidades") or [])
    coincidentes = sorted(requeridas & del_candidato)
    faltantes = sorted(requeridas - del_candidato)
    if requeridas:
        componentes["habilidades"] = len(coincidentes) / len(requeridas)
        explicacion.append(f"Cumple {len(coincidentes)} de {len(requeridas)} habilidades requeridas.")
        if faltantes:
            explicacion.append("Le faltan: " + ", ".join(faltantes) + ".")
    else:
        explicacion.append("La vacante no define habilidades específicas.")

    texto_vacante = f"{vacante.get('titulo', '')} {vacante.get('descripcion', '')} {vacante.get('requisitos', '')}"
    texto_candidato = f"{candidato.get('cv_texto', '')} {' '.join(del_candidato)}"
    coseno = similitud_coseno(texto_vacante, texto_candidato, corpus)
    componentes["texto"] = min(1.0, coseno / COSENO_REFERENCIA)
    explicacion.append(f"Similitud entre el perfil y la descripción de la vacante: {round(coseno * 100)}%.")

    minimo = vacante.get("experiencia_minima_anios") or 0
    anios = candidato.get("anios_experiencia") or 0
    if minimo > 0:
        componentes["experiencia"] = min(1.0, anios / minimo)
        if anios >= minimo:
            explicacion.append(f"Experiencia suficiente ({anios} años; se piden {minimo}).")
        else:
            explicacion.append(f"Experiencia por debajo de lo pedido ({anios} de {minimo} años).")

    nivel_min = nivel_a_numero(vacante.get("nivel_educacion_minimo"))
    nivel_cand = nivel_a_numero(candidato.get("nivel_educacion"))
    if nivel_min > 0:
        componentes["educacion"] = 1.0 if nivel_cand >= nivel_min else nivel_cand / nivel_min
        if nivel_cand >= nivel_min:
            explicacion.append("Cumple el nivel educativo mínimo.")
        else:
            explicacion.append(f"No alcanza el nivel educativo mínimo ({vacante.get('nivel_educacion_minimo')}).")

    peso_total = sum(PESOS[c] for c in componentes)
    score = 100 * sum(PESOS[c] * v for c, v in componentes.items()) / peso_total
    score = round(score, 1)

    return {
        "score": score,
        "clasificacion": clasificar(score),
        "desglose": {c: round(v * 100, 1) for c, v in componentes.items()},
        "habilidades_coincidentes": coincidentes,
        "habilidades_faltantes": faltantes,
        "explicacion": explicacion,
    }
