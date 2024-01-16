from enum import IntEnum

from src._types import AppStrEnum


class Env(IntEnum):
    PRD = 0
    DEV = 1


class ReservedRoleSlug(AppStrEnum):
    ADMIN = "admin"
