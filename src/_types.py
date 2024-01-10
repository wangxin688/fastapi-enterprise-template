from enum import Enum
from typing import Annotated, Generic, ParamSpec, TypeVar

from pydantic import BaseModel, ConfigDict, constr
from pydantic.functional_validators import BeforeValidator

from src.validators import items_to_list, mac_address_validator

T = TypeVar("T")
P = ParamSpec("P")

StrList = Annotated[str | list[str], BeforeValidator(items_to_list)]
IntList = Annotated[int | list[int], BeforeValidator(items_to_list)]
MacAddress = Annotated[str, BeforeValidator(mac_address_validator)]
NameStr = constr(pattern="^[a-zA-Z0-9_-].$", max_length=50)
NameChineseStr = constr(pattern="^[\u4e00-\u9fa5a-zA-Z0-9_-].$", max_length=50)


class ResponseBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BaseResponse(BaseModel, Generic[T]):
    code: int | None = 0
    data: T | None = None
    message: str | None = "success"


class ListT(BaseModel, Generic[T]):
    count: int
    results: T | None = None


class BaseListResponse(BaseModel, Generic[T]):
    code: int | None = 0
    data: ListT
    message: str | None = "success"


class AppStrEnum(str, Enum):
    def __str__(self) -> str:
        return str.__str__(self)

    @classmethod
    def to_list(cls) -> list[str]:
        return [c.value for c in cls]
