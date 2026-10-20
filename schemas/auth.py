from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from schemas.candidate import Name

Code = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]
Role = Literal["admin", "recruiter", "candidate"]


class RegisterInput(BaseModel):
    """Open sign-up, only for candidates."""

    name: Name
    email: EmailStr
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None


class LoginInput(BaseModel):
    email: EmailStr


class VerifyInput(BaseModel):
    email: EmailStr
    code: Code


class DemoLoginInput(BaseModel):
    account: Literal["recruiter", "candidate"]


class CodeSent(BaseModel):
    message: str
    email: str


class AuthOptions(BaseModel):
    demo_login: bool


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    candidate_id: int | None
    is_active: bool
    verified: bool
    created_at: datetime
    last_login: datetime | None


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class StaffUserCreate(BaseModel):
    """Admins create staff accounts; they enter with a code sent to that email."""

    name: Name
    email: EmailStr
    role: Literal["admin", "recruiter"]


class UserUpdate(BaseModel):
    name: Name | None = None
    role: Literal["admin", "recruiter"] | None = None
    is_active: bool | None = None
