from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from polyfactory.fields import Ignore

from src.features.admin.models import Group, Menu, Permission, Role, User
from src.features.admin.security import get_password_hash


class UserFactory(SQLAlchemyFactory[User]):
    __model__ = User
    __set_foreign_keys__ = False
    id = Ignore()
    password = get_password_hash("admin123")


class GroupFactory(SQLAlchemyFactory[Group]):
    __model__ = Group
    __set_foreign_keys__ = False
    id = Ignore()


class RoleFactory(SQLAlchemyFactory[Role]):
    __model__ = Role
    __set_foreign_keys__ = False
    id = Ignore()


class PermissionFactory(SQLAlchemyFactory[Permission]):
    __set_foreign_keys__ = False
    __model__ = Permission


class MenuFactory(SQLAlchemyFactory[Menu]):
    __model__ = Menu
    __set_foreign_keys__ = False
    id = Ignore()

    permission = [1, 2, 3, 4]  # noqa: RUF012
