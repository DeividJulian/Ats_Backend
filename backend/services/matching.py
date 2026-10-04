"""Une la base de datos con el cálculo de match: arma los datos y el corpus para TF-IDF."""
from sqlalchemy.orm import Session

from models.candidato import Candidato
from models.vacante import Vacante
from services.scoring import calcular_match


def a_dict_vacante(v: Vacante) -> dict:
    return {
        "titulo": v.titulo,
        "descripcion": v.descripcion,
        "requisitos": v.requisitos,
        "habilidades_requeridas": v.habilidades_requeridas or [],
        "experiencia_minima_anios": v.experiencia_minima_anios,
        "nivel_educacion_minimo": v.nivel_educacion_minimo,
    }


def a_dict_candidato(c: Candidato) -> dict:
    return {
        "cv_texto": c.cv_texto,
        "habilidades": c.habilidades or [],
        "anios_experiencia": c.anios_experiencia,
        "nivel_educacion": c.nivel_educacion,
    }


def corpus_del_sistema(db: Session) -> list[str]:
    """Todos los textos conocidos: ayudan a que los términos comunes pesen menos y los distintivos más."""
    textos = [f"{v.titulo} {v.descripcion} {v.requisitos}" for v in db.query(Vacante).all()]
    textos += [c.cv_texto for c in db.query(Candidato).all() if c.cv_texto]
    return textos


def evaluar(db: Session, vacante: Vacante, candidato: Candidato, corpus: list[str] | None = None) -> dict:
    if corpus is None:
        corpus = corpus_del_sistema(db)
    return calcular_match(a_dict_vacante(vacante), a_dict_candidato(candidato), corpus)
