from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    """Account that logs in with a code sent to its email (no passwords)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)  # always lowercase
    # Left from the password login; no longer used and kept only so old databases still load
    password_hash = Column(String, nullable=True)
    # "admin", "recruiter" or "candidate"
    role = Column(String, nullable=False)
    # Only for candidates: the profile the recruiters see
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    # True after the first correct code: until then the account can't be used
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_login = Column(DateTime(timezone=True), nullable=True)

    candidate = relationship("Candidate")
    codes = relationship("VerificationCode", cascade="all, delete-orphan", passive_deletes=True)


class VerificationCode(Base):
    """Six-digit code sent by email. Only its HMAC is stored, and it works once."""

    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    purpose = Column(String, nullable=False)  # "signup" or "login"
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
