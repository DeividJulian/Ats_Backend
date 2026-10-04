from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),)

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    details = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="nuevo")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    job = relationship("Job")
    candidate = relationship("Candidate")
