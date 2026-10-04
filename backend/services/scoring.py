"""Explainable computation of the match score between a job and a candidate."""
from services.profile import level_to_number
from services.similarity import cosine_similarity

# Criterion names are returned to the client in the score breakdown, so they stay in Spanish
WEIGHTS = {"habilidades": 0.50, "texto": 0.20, "experiencia": 0.20, "educacion": 0.10}

# Cosines between real texts rarely exceed 0.30, so the value is scaled so that 0.30 counts as a full match
REFERENCE_COSINE = 0.30


def classify(score: float) -> str:
    if score >= 75:
        return "alto"
    if score >= 50:
        return "medio"
    return "bajo"


def compute_match(job: dict, candidate: dict, corpus: list[str] | None = None) -> dict:
    """
    job: title, description, requirements, required_skills, min_experience_years, min_education_level
    candidate: resume_text, skills, experience_years, education_level
    Only what the job actually requires is evaluated: criteria without a requirement are skipped
    and the weights are redistributed among the rest.
    """
    explanation = []
    components = {}  # criterion -> score from 0 to 1

    required = set(job.get("required_skills") or [])
    candidate_skills = set(candidate.get("skills") or [])
    matching = sorted(required & candidate_skills)
    missing = sorted(required - candidate_skills)
    if required:
        components["habilidades"] = len(matching) / len(required)
        explanation.append(f"Cumple {len(matching)} de {len(required)} habilidades requeridas.")
        if missing:
            explanation.append("Le faltan: " + ", ".join(missing) + ".")
    else:
        explanation.append("La vacante no define habilidades específicas.")

    job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}"
    candidate_text = f"{candidate.get('resume_text', '')} {' '.join(candidate_skills)}"
    cosine = cosine_similarity(job_text, candidate_text, corpus)
    components["texto"] = min(1.0, cosine / REFERENCE_COSINE)
    explanation.append(f"Similitud entre el perfil y la descripción de la vacante: {round(cosine * 100)}%.")

    min_years = job.get("min_experience_years") or 0
    years = candidate.get("experience_years") or 0
    if min_years > 0:
        components["experiencia"] = min(1.0, years / min_years)
        if years >= min_years:
            explanation.append(f"Experiencia suficiente ({years} años; se piden {min_years}).")
        else:
            explanation.append(f"Experiencia por debajo de lo pedido ({years} de {min_years} años).")

    min_level = level_to_number(job.get("min_education_level"))
    candidate_level = level_to_number(candidate.get("education_level"))
    if min_level > 0:
        components["educacion"] = 1.0 if candidate_level >= min_level else candidate_level / min_level
        if candidate_level >= min_level:
            explanation.append("Cumple el nivel educativo mínimo.")
        else:
            explanation.append(f"No alcanza el nivel educativo mínimo ({job.get('min_education_level')}).")

    total_weight = sum(WEIGHTS[c] for c in components)
    score = 100 * sum(WEIGHTS[c] * v for c, v in components.items()) / total_weight
    score = round(score, 1)

    # Keys are returned to the client as-is, so they stay in Spanish
    return {
        "score": score,
        "clasificacion": classify(score),
        "desglose": {c: round(v * 100, 1) for c, v in components.items()},
        "habilidades_coincidentes": matching,
        "habilidades_faltantes": missing,
        "explicacion": explanation,
    }
