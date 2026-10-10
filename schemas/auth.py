from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from schemas.candidate import Name

Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
Role = Literal["admin", "recruiter", "candidate"]


class LoginInput(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class RegisterInput(BaseModel):
    name: Name
    email: EmailStr
    password: Password
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    candidate_id: int | None
    is_active: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class StaffUserCreate(BaseModel):
    """Admins create staff accounts; candidates sign up by themselves."""

    name: Name
    email: EmailStr
    password: Password
    role: Literal["admin", "recruiter"]


class UserUpdate(BaseModel):
    name: Name | None = None
    role: Literal["admin", "recruiter"] | None = None
    is_active: bool | None = None
    password: Password | None = None
