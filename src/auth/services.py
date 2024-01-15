from src.auth import schemas
from src.auth.models import Group, Role, User
from src.db.crud import DtoBase


class UserDto(DtoBase[User, schemas.UserCreate, schemas.UserUpdate, schemas.UserQuery]):
    ...


class GroupDto(DtoBase[Group, schemas.GroupCreate, schemas.GroupUpdate, schemas.GroupQuery]):
    ...


class RoleDto(DtoBase[Role, schemas.RoleCreate, schemas.RoleUpdate, schemas.RoleQuery]):
    ...


user_dto = UserDto(User)
group_dto = UserDto(Group)
role_dto = RoleDto(Role)
