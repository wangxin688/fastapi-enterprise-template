from src.auth.models import Group, Permission, Role, RolePermission, User  # noqa: F401
from src.db.base import Base


def orm_by_table_name(table_name: str) -> type[Base] | None:
    for m in Base.registry.mappers:
        if getattr(m.class_, "__tablename__", None) == table_name:
            return m.class_
    return None
