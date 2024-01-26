from datetime import datetime
from enum import Enum
from typing import Annotated, Generic, Literal, ParamSpec, TypeAlias, TypedDict, TypeVar

import pydantic
from fastapi import Query
from pydantic import ConfigDict, Field, constr
from pydantic.functional_validators import BeforeValidator

from src.validators import items_to_list, mac_address_validator

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")

Order: TypeAlias = Literal["descend", "ascend"]

StrList = Annotated[str | list[str], BeforeValidator(items_to_list)]
IntList = Annotated[int | list[int], BeforeValidator(items_to_list)]
MacAddress = Annotated[str, BeforeValidator(mac_address_validator)]
NameStr = constr(pattern="^[a-zA-Z0-9_-].$", max_length=50)
NameChineseStr = constr(pattern="^[\u4e00-\u9fa5a-zA-Z0-9_-].$", max_length=50)


class BaseModel(pydantic.BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AuditTime(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None


class AuditUserBase(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None


class AuditUser(BaseModel):
    created_by: AuditUserBase | None = None
    updated_by: AuditUserBase | None = None


class ListT(BaseModel, Generic[T]):
    count: int
    results: T | None = None


class AppStrEnum(str, Enum):
    def __str__(self) -> str:
        return str.__str__(self)

    @classmethod
    def to_list(cls) -> list[str]:
        return [c.value for c in cls]


class AuditTimeQuery(BaseModel):
    created_at__lte: datetime
    created_at__gte: datetime
    updated_at__lte: datetime
    updated_at__gte: datetime


class AuidtUserQuery(BaseModel):
    created_by_fk: list[int] = Field(Query(default=[]))
    updated_by_fk: list[int] = Field(Query(default=[]))


class QueryParams(BaseModel):
    limit: int | None = Query(default=20, ge=0, le=1000, description="Number of results to return per request.")
    offset: int | None = Query(default=0, ge=0, description="The initial index from which return the results.")
    q: str | None = Query(default=None, description="Search for results.")
    id: list[int] | None = Field(Query(default=[], description="request object unique ID"))
    order_by: str | None = Query(default=None, description="Which field to use when order the results")
    order: Order | None = Query(default="ascend", description="Order by dscend or ascend")


class BatchDelete(BaseModel):
    ids: list[int]


class BatchUpdate(BaseModel):
    ids: list[int]


class I18nField(BaseModel):
    en_US: str  # noqa: N815
    zh_CN: str  # noqa: N815


class VisibleName(TypedDict, total=True):
    en_US: str
    zh_CN: str


class IdResponse(BaseModel):
    id: int
