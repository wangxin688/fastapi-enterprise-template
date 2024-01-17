from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import errors
from src._types import ListT, ResultT
from src.auth import schemas
from src.auth.models import Group, Role, User
from src.auth.services import user_dto
from src.cbv import cbv
from src.deps import auth, get_session
from src.exceptions import GenerError

router = APIRouter()


@cbv(router)
class UserCBV:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)

    @router.post("/users", operation_id="e0fe80d5-cbe0-4c2c-9eff-57e80ecba522")
    async def create_user(self, user: schemas.UserCreate) -> ResultT[int]:
        new_user = await user_dto.create(self.session, user)
        return ResultT(id=new_user.id)

    @router.get("/users/{id}", operation_id="8057d614-150f-42ee-984c-d0af35796da3")
    async def get_user(self, id: int) -> schemas.UserDetail:
        db_user = await user_dto.get_one_or_404(
            self.session,
            id,
            options=(
                selectinload(User.role).load_only(Role.id, Role.name),
                selectinload(User.group).load_only(Group.id, Group.name),
            ),
        )
        return schemas.UserDetail.model_validate(db_user)

    @router.get("/users", operation_id="c5f793b1-7adf-4b4e-a498-732b0fa7d758")
    async def get_users(self, query: schemas.UserQuery) -> ListT[list[schemas.UserDetail]]:
        count, results = await user_dto.list_and_count(
            self.session,
            query,
            options=(
                selectinload(User.role).load_only(Role.id, Role.name),
                selectinload(User.group).load_only(Group.id, Group.name),
            ),
        )
        return ListT(count=count, results=results)

    @router.put("/users/{id}", operation_id="2fda2e00-ad86-4296-a1d4-c7f02366b52e")
    async def update_user(self, id: int, user: schemas.UserUpdate) -> ResultT[int]:
        update_user = user.model_dump(exclude_unset=True)
        if "password" in update_user and update_user["password"] is None:
            raise GenerError(errors.ERR_10006, status_code=status.HTTP_406_NOT_ACCEPTABLE)
        db_user = await user_dto.get_one_or_404(self.session, id)
        await user_dto.update(self.session, db_user, user)
        return ResultT(data=id)
