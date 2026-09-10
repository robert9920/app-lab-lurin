from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Model):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Password(Model):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    password: str = Field(min_length=15, max_length=128)


class Version(Model):
    version: int = Field(gt=0, strict=True)


class Sample(Model):
    client_code: str = Field(min_length=1, max_length=100)
    borehole: str = Field(default="", max_length=100)
    material: str = Field(default="Suelo", max_length=100)
    depth_from: Decimal | None = Field(default=None, ge=0)
    depth_to: Decimal | None = Field(default=None, ge=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str = Field(default="kg", min_length=1, max_length=20)
    notes: str = Field(default="", max_length=3000)
    assay_ids: list[UUID] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def valid_sample(self):
        if self.depth_from is not None and self.depth_to is not None and self.depth_to < self.depth_from:
            raise ValueError("Profundidades inválidas")
        if len(set(self.assay_ids)) != len(self.assay_ids):
            raise ValueError("Ensayos duplicados")
        return self


class RequestCreate(Model):
    project_id: UUID
    title: str = Field(min_length=3, max_length=180)
    notes: str = Field(default="", max_length=5000)
    target_date: date | None = None
    samples: list[Sample] = Field(min_length=1, max_length=200)


class RequestEdit(RequestCreate, Version):
    pass


class Action(Version):
    action: Literal["submit", "approve", "observe", "reject", "close"]
    reason: str = Field(default="", max_length=3000)


class ReceivedSample(Model):
    sample_id: UUID
    codigo_recepcion: str = Field(min_length=1, max_length=60)
    codigo_laboratorio: str = Field(min_length=1, max_length=60)
    condition: Literal["OK", "OBSERVED", "DAMAGED", "INSUFFICIENT"] = "OK"
    received_quantity: Decimal | None = Field(default=None, gt=0)
    reception_notes: str = Field(default="", max_length=3000)

    @field_validator("codigo_recepcion", "codigo_laboratorio")
    @classmethod
    def normalize_code(cls, value):
        return value.upper()

    @model_validator(mode="after")
    def reason(self):
        if self.condition != "OK" and not self.reception_notes:
            raise ValueError("Describe la observación")
        return self


class Reception(Version):
    received_at: datetime
    transport: str = Field(default="", max_length=200)
    reason: str = Field(default="", max_length=3000)
    samples: list[ReceivedSample] = Field(min_length=1, max_length=200)

    @field_validator("received_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("Incluye zona horaria")
        return value


class TaskUpdate(Version):
    task_ids: list[UUID] = Field(min_length=1, max_length=200)
    action: Literal["assign", "start", "observe", "complete", "cancel", "resume"]
    technician_id: UUID | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    reason: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def dates(self):
        if self.planned_start and self.planned_end and self.planned_end < self.planned_start:
            raise ValueError("Fechas inválidas")
        return self


class Comment(Version):
    body: str = Field(min_length=1, max_length=5000)
    internal: bool = False


class TaskSelection(Version):
    request_id: UUID
    task_ids: list[UUID] = Field(min_length=1, max_length=200)


class WorkUpdate(Model):
    requests: list[TaskSelection] = Field(min_length=1, max_length=100)
    action: Literal["assign", "start", "observe", "complete", "cancel", "resume"]
    technician_id: UUID | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    reason: str = Field(default="", max_length=3000)


class Organization(Model):
    name: str = Field(min_length=2, max_length=200)
    tax_id: str = Field(default="", max_length=30)


class Project(Model):
    organization_id: UUID
    code: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=3, max_length=250)
    location: str = Field(default="", max_length=250)


class UserCreate(Password):
    email: EmailStr
    organization_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    roles: list[Literal["ADMIN", "MANAGER", "TECH", "CLIENT"]] = Field(min_length=1, max_length=4)
    project_ids: list[UUID] = Field(default_factory=list, max_length=100)


class UserEdit(Model):
    organization_id: UUID | None = None
    roles: list[Literal["ADMIN", "MANAGER", "TECH", "CLIENT"]] = Field(min_length=1, max_length=4)
    active: bool
    project_ids: list[UUID] = Field(default_factory=list, max_length=100)


class Catalog(Model):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=3, max_length=200)
    method: str = Field(default="", max_length=200)
    category: str = Field(default="Geotecnia", max_length=100)
    active: bool = True
