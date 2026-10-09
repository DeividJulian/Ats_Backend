"""Generated insights: profile summary, skills to develop, training suggestions and interview guides.

Every text produced here is shown to the user, so it is written in Spanish.
"""
from collections import Counter

from services.profile import LEVEL_LABELS
from services.skills import infer_skills, skill_area

AREA_LABELS = {
    "technology": "tecnología",
    "administration": "administración y finanzas",
    "sales": "comercial y mercadeo",
    "soft_skills": "habilidades blandas y gestión",
    "general": "general",
}

TRAINING_BY_AREA = {
    "technology": "Curso práctico de {skill} con un proyecto propio (por ejemplo en SENA Sofía Plus, "
                  "freeCodeCamp o la documentación oficial).",
    "administration": "Curso de {skill} aplicado a pymes (por ejemplo en SENA Sofía Plus) y práctica con casos reales.",
    "sales": "Taller de {skill} con práctica en situaciones reales con clientes.",
    "soft_skills": "Taller o mentoría en {skill} y práctica en proyectos de equipo.",
    "general": "Formación introductoria en {skill}.",
}

AREA_QUESTIONS = {
    "technology": [
        "Describa cómo encontraría y corregiría un error que solo ocurre en producción.",
        "¿Cómo se asegura de que su trabajo sea fácil de mantener por otras personas?",
    ],
    "administration": [
        "¿Cómo verifica que la información contable o administrativa que entrega no tenga errores?",
        "Cuéntenos cómo organiza sus tareas en los cierres de mes o cuando hay fechas límite.",
    ],
    "sales": [
        "Cuéntenos de una venta difícil que logró cerrar. ¿Qué hizo diferente?",
        "¿Cómo responde a un cliente que considera que el precio es muy alto?",
    ],
    "soft_skills": [
        "Describa un conflicto en un equipo de trabajo y cómo ayudó a resolverlo.",
        "¿Cómo comunica una mala noticia a su jefe o a un cliente?",
    ],
    "general": [
        "Cuéntenos el logro profesional del que se sienta más orgulloso.",
    ],
}


def _join(items: list[str]) -> str:
    """'a', 'a y b', 'a, b y c'."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def main_area(skills: list[str]) -> str:
    areas = Counter(skill_area(s) for s in skills)
    return areas.most_common(1)[0][0] if areas else "general"


def skills_by_area(skills: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for skill in sorted(skills):
        grouped.setdefault(skill_area(skill), []).append(skill)
    return grouped


def training_for(skill: str) -> str:
    return TRAINING_BY_AREA[skill_area(skill)].format(skill=skill)


def candidate_summary(skills: list[str], experience_years: int, education_level: str | None) -> str:
    level = LEVEL_LABELS.get(education_level or "")
    sentences = [
        (f"Perfil de nivel {level}" if level else "Perfil sin nivel educativo detectado")
        + (f" con {experience_years} años de experiencia." if experience_years else " sin experiencia registrada.")
    ]
    if skills:
        sentences.append(f"Sus habilidades principales son {_join(sorted(skills)[:5])}.")
        sentences.append(f"Su perfil se orienta al área de {AREA_LABELS[main_area(skills)]}.")
    else:
        sentences.append("No se detectaron habilidades del catálogo en su hoja de vida.")
    return " ".join(sentences)


def candidate_insights(skills: list[str], experience_years: int, education_level: str | None,
                       open_jobs_skills: list[list[str]]) -> dict:
    """open_jobs_skills: the required skills of each open job, to find what the market asks for."""
    have = set(skills) | set(infer_skills(skills))
    demand = Counter(s for job_skills in open_jobs_skills for s in set(job_skills) if s not in have)
    return {
        "summary": candidate_summary(skills, experience_years, education_level),
        "main_area": main_area(skills),
        "skills_by_area": skills_by_area(skills),
        "inferred_skills": infer_skills(skills),
        "skills_to_develop": [
            {"skill": s, "open_jobs_requiring": n, "suggestion": training_for(s)} for s, n in demand.most_common(5)
        ],
    }


def interview_questions(job_title: str, job_skills: list[str], min_years: int, result: dict,
                        candidate_years: int) -> list[dict]:
    questions = []
    for skill in result.get("matching_skills", [])[:3]:
        questions.append({
            "type": "strength",
            "question": f"Cuéntenos un proyecto concreto en el que haya usado {skill}. ¿Qué resultado obtuvo?",
        })
    for skill, source in list(result.get("inferred_skills", {}).items())[:2]:
        questions.append({
            "type": "inferred",
            "question": f"Su experiencia con {source} sugiere que conoce {skill}. ¿Lo ha usado directamente? ¿En qué?",
        })
    for skill in result.get("missing_skills", [])[:3]:
        questions.append({
            "type": "gap",
            "question": f"La vacante requiere {skill}. ¿Qué experiencia tiene con esta habilidad y cómo la fortalecería?",
        })
    if min_years and candidate_years < min_years:
        questions.append({
            "type": "experience",
            "question": f"La vacante pide {min_years} años de experiencia y su perfil registra {candidate_years}. "
                        "¿Qué experiencias adicionales (prácticas, proyectos, voluntariados) considera relevantes?",
        })
    for question in AREA_QUESTIONS[main_area(job_skills)]:
        questions.append({"type": "area", "question": question})
    questions.append({
        "type": "motivation",
        "question": f"¿Por qué le interesa el cargo de {job_title} y qué aportaría en los primeros tres meses?",
    })
    return questions


def interview_guide(job_title: str, job_skills: list[str], min_years: int, result: dict,
                    candidate_years: int) -> dict:
    strengths = result.get("matching_skills", [])
    gaps = result.get("missing_skills", [])
    if result.get("classification") == "high":
        focus = "Candidato con alto ajuste: valide la profundidad de sus fortalezas y su motivación."
    elif result.get("classification") == "medium":
        focus = "Ajuste medio: concentre la entrevista en las brechas y en su capacidad de aprenderlas."
    else:
        focus = "Ajuste bajo: valide si sus brechas pueden cerrarse rápido antes de avanzar en el proceso."
    return {
        "focus": focus,
        "strengths": strengths,
        "gaps": gaps,
        "questions": interview_questions(job_title, job_skills, min_years, result, candidate_years),
        "training_for_gaps": [{"skill": s, "suggestion": training_for(s)} for s in gaps],
    }
