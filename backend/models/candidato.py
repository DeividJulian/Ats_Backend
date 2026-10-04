from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from database import Base


def ahora():
    return datetime.now(timezone.utc)


class Candidato(Base):
    __tablename__ = "candidatos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    telefono = Column(String, nullable=True)
    cv_texto = Column(Text, nullable=False, default="")
    habilidades = Column(JSON, nullable=False, default=list)
    anios_experiencia = Column(Integer, nullable=False, default=0)
    nivel_educacion = Column(String, nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
