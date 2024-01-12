from typing import NamedTuple


class ErrorCode(NamedTuple):
    code: int
    message: str


ERR_500 = ErrorCode(500, "app.internal_server_error")
