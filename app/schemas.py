from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Username = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")


class RegisterRequest(BaseModel):
    username: str = Username
    password: str = Field(min_length=10, max_length=128)
    bootstrap_token: str | None = Field(default=None, max_length=256)


class LoginRequest(BaseModel):
    username: str = Username
    password: str = Field(min_length=10, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "user"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=2000)
    visibility: Literal["private", "public"] = "private"

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name cannot be blank")
        return value.strip()


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    visibility: Literal["private", "public"] | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    visibility: str
    owner_id: int
    created_at: datetime


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    version: str
    original_filename: str
    artifact_format: str
    sha256: str
    size_bytes: int
    created_at: datetime


class GrantRequest(BaseModel):
    username: str = Username
    can_infer: bool = True


class GrantResponse(BaseModel):
    username: str
    can_infer: bool


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    key: str
    prefix: str


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    prefix: str
    created_at: datetime
    revoked_at: datetime | None


class InferenceRequest(BaseModel):
    features: list[float] = Field(min_length=1, max_length=4096)


class InferenceResponse(BaseModel):
    project_id: str
    version: str
    output: float
