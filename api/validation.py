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
    id: UUID | None = None
    client_code: str = Field(min_length=1, max_length=100)
    borehole: str = Field(default="", max_length=100)
    material: str = Field(min_length=1, max_length=100)
    depth_from: Decimal | None = Field(default=None, ge=0)
    depth_to: Decimal | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, gt=0, strict=True)
    weight: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    notes: str = Field(default="", max_length=3000)
    assay_ids: list[UUID] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def valid_sample(self):
        if self.depth_from is not None and self.depth_to is not None and self.depth_to < self.depth_from:
            raise ValueError("Profundidades inválidas")
        if len(set(self.assay_ids)) != len(self.assay_ids):
            raise ValueError("Ensayos duplicados")
        return self


class RequestCreate(Model):
    project_id: str | None = Field(default=None, min_length=1, max_length=100)
    title: str = Field(min_length=3, max_length=180)
    notes: str = Field(default="", max_length=5000)
    target_date: date | None = None
    district: str = Field(min_length=1, max_length=100)
    province: str = Field(min_length=1, max_length=100)
    department: str = Field(min_length=1, max_length=100)
    easting: Decimal | None = Field(default=None, allow_inf_nan=False)
    northing: Decimal | None = Field(default=None, allow_inf_nan=False)
    samples: list[Sample] = Field(min_length=1, max_length=200)


class RequestEdit(RequestCreate, Version):
    pass


class SampleAssays(Model):
    sample_id: UUID
    assay_ids: list[UUID] = Field(max_length=40)

    @field_validator("assay_ids")
    @classmethod
    def unique_assays(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Ensayos duplicados")
        return values


class AssaysEdit(Version):
    samples: list[SampleAssays] = Field(min_length=1, max_length=200)


class AssayDecision(Model):
    task_id: UUID
    decision: Literal["APPROVED", "REJECTED"]
    reason: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def rejection_reason(self):
        if self.decision == "REJECTED" and not self.reason:
            raise ValueError("Indica el motivo del rechazo")
        return self


class AssaysReview(Version):
    decisions: list[AssayDecision] = Field(min_length=1, max_length=200)


class AssaysResubmit(Version):
    task_ids: list[UUID] = Field(min_length=1, max_length=200)


def validate_coordinates(data, previous=None):
    # Historical values remain readable; validate only newly supplied/changed values.
    from errors import AppError

    for field, lower, upper, label in (
        ("easting", 100000, 1000000, "Coordenadas Este: debe tener seis dígitos enteros"),
        ("northing", 1000000, 10000000, "Coordenadas Norte: debe tener siete dígitos enteros"),
    ):
        value = getattr(data, field)
        if previous is not None and value == previous[field]:
            continue
        if value is not None and not lower <= value < upper:
            raise AppError(400, label + "; se permiten decimales.")


class Action(Version):
    action: Literal["submit", "approve", "observe", "reject", "close"]
    reason: str = Field(default="", max_length=3000)


class ReceivedSample(Model):
    sample_id: UUID
    codigo_recepcion: str = Field(min_length=1, max_length=60)
    codigo_laboratorio: str = Field(min_length=1, max_length=60)
    condition: Literal["OK", "OBSERVED", "DAMAGED", "INSUFFICIENT"] = "OK"
    received_quantity: int | None = Field(default=None, gt=0, strict=True)
    received_weight: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
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
    active: bool = True
    is_internal: bool = False


class OrganizationEdit(Organization):
    active: bool
    is_internal: bool = False


class WorkOrder(Version):
    codigo_ot: str = Field(min_length=1, max_length=60)
    reason: str = Field(default="", max_length=3000)

    @field_validator("codigo_ot")
    @classmethod
    def normalize_code(cls, value):
        return value.upper()


class UserCreate(Password):
    email: EmailStr
    organization_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    roles: list[Literal["ADMIN", "MANAGER", "TECH", "CLIENT"]] = Field(min_length=1, max_length=4)
    phone: str | None = Field(default=None, max_length=30)


class UserEdit(Model):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    organization_id: UUID | None = None
    roles: list[Literal["ADMIN", "MANAGER", "TECH", "CLIENT"]] = Field(min_length=1, max_length=4)
    active: bool


class Catalog(Model):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=3, max_length=200)
    method: str = Field(default="", max_length=200)
    category: str = Field(default="Geotecnia", max_length=100)
    active: bool = True
