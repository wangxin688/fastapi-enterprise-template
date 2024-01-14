from ipaddress import UUID, IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from typing import Any

from src.context import locale_ctx


def error_message_value_handler(value: Any) -> Any:
    if isinstance(value, dict) and "en_US" in value:
        return value[locale_ctx.get()]
    if isinstance(value, IPv4Address | IPv6Address | IPv4Network | IPv6Network | IPv4Interface | IPv6Interface | UUID):
        return str(value)
    if isinstance(value, list):
        return [str(_v) for _v in value]
    return value


class TokenNotProvideError(Exception):
    ...


class TokenInvalidError(Exception):
    ...


class TokenExpireError(Exception):
    ...


class PermissionDenyError(Exception):
    ...


class NotFoundError(Exception):
    def __init__(self, name: str, field: str, value: Any) -> None:
        self.name = name
        self.field = field
        self.value = error_message_value_handler(value)

    def __repr__(self) -> str:
        return f"Object:{self.name} with field:{self.field}-value:{self.value} not found."


class ExistError(Exception):
    def __init__(self, name: str, field: str, value: Any) -> None:
        self.name = name
        self.field = field
        self.value = error_message_value_handler(value)

    def __repr__(self) -> str:
        return f"Object:{self.name} with field:{self.field}-value:{self.value} already exist."


sentry_ignore_errors = [
    TokenExpireError,
    TokenInvalidError,
    TokenNotProvideError,
    PermissionDenyError,
    NotFoundError,
    ExistError,
]
