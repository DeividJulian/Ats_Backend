from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


def ahora():
    return datetime.now(timezone.utc)


class Postulacion(Base):
    __tablename__ = "postulaciones"
    __table_args__ = (UniqueConstraint("vacante_id", "candidato_id", name="uq_postulacion_vacante_candidato"),)

    id = Column(Integer, primary_key=True, index=True)
    vacante_id = Column(Integer, ForeignKey("vacantes.id"), nullable=False)
    candidato_id = Column(Integer, ForeignKey("candidatos.id"), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    detalle = Column(JSON, nullable=False, default=dict)
    estado = Column(String, nullable=False, default="nuevo")
    creada_en = Column(DateTime(timezone=True), nullable=False, default=ahora)

    vacante = relationship("Vacante")
    candidato = relationship("Candidato")
