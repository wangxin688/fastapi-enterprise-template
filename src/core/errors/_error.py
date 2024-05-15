from typing import Any, NamedTuple, TypedDict


class Error(TypedDict):
    code: int
    message: str
    details: list[Any] | None


class ErrorCode(NamedTuple):
    error: int
    message: str
    details: list[Any] | None = None

    def dict(self) -> "Error":
        return {"code": self.error, "message": self.message, "details": self.details}
