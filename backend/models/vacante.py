from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from database import Base


def ahora():
    return datetime.now(timezone.utc)


class Vacante(Base):
    __tablename__ = "vacantes"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=False)
    requisitos = Column(Text, nullable=False, default="")
    habilidades_requeridas = Column(JSON, nullable=False, default=list)
    experiencia_minima_anios = Column(Integer, nullable=False, default=0)
    nivel_educacion_minimo = Column(String, nullable=True)
    estado = Column(String, nullable=False, default="abierta")
    creada_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
