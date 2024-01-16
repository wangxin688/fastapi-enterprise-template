from typing import Any, NamedTuple


class ErrorCode(NamedTuple):
    error: int
    message: str
    details: list[Any] | None = None

    def dict(self):  # noqa: ANN201
        return self._asdict()


ERR_404 = ErrorCode(404, "app.not_found")
ERR_409 = ErrorCode(409, "app.already_exist")
ERR_500 = ErrorCode(500, "app.internal_server_error")
ERR_10001 = ErrorCode(10001, "User's password can not set as null.")
ERR_10002 = ErrorCode(10002, "Invalid bearer token.")
ERR_10003 = ErrorCode(10003, "Bearer token was expired.")
ERR_10004 = ErrorCode(10004, "Bearer token is invalid for refresh token was provided.")
ERR_10005 = ErrorCode(10005, "Permission deny, user with limited access for current API.")
ERR_10005 = ErrorCode(10005, "Permission deny, user with limited access for current API.")
ERR_10006 = ErrorCode(10006, "Update user failed, password can not be null.")
