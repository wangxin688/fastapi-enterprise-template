from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import errors
from src._types import IdResponse, ListResultT, ListT, ResultT
from src.auth import schemas
from src.auth.models import Group, Role, User
from src.auth.services import group_dto, user_dto
from src.cbv import cbv
from src.deps import auth, get_session
from src.exceptions import GenerError

router = APIRouter()


@cbv(router)
class UserCbv:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)

    @router.post("/users", operation_id="e0fe80d5-cbe0-4c2c-9eff-57e80ecba522")
    async def create_user(self, user: schemas.UserCreate) -> ResultT[IdResponse]:
        """
        Create a new user.

        Args:
            user (schemas.UserCreate): The user data to create.

        Returns:
            ResultT[int]: The ID of the newly created user.
        """
        new_user = await user_dto.create(self.session, user)
        result = await user_dto.commit(self.session, new_user)
        return ResultT(data=IdResponse(id=result.id))

    @router.get("/users/{id}", operation_id="8057d614-150f-42ee-984c-d0af35796da3")
    async def get_user(self, id: int) -> ResultT[schemas.UserDetail]:
        """
        Get a user by their ID.

        Args:
            id (int): The ID of the user.

        Returns:
            UserDetail: The detailed information of the user.

        Raises:
            HTTPException: If the user with the specified ID is not found.
        """
        db_user = await user_dto.get_one_or_404(
            self.session,
            id,
            options=(
                selectinload(User.role).load_only(Role.id, Role.name),
                selectinload(User.group).load_only(Group.id, Group.name),
            ),
        )
        return ResultT(data=schemas.UserDetail.model_validate(db_user))

    @router.get("/users", operation_id="c5f793b1-7adf-4b4e-a498-732b0fa7d758")
    async def get_users(self, query: schemas.UserQuery) -> ListResultT[list[schemas.UserDetail]]:
        """
        Get a list of users based on the provided query parameters.

        Args:
            query (schemas.UserQuery): The query parameters to filter the users.

        Returns:
            ListT[list[schemas.UserDetail]]: A list of user details matching the query.
        """
        count, results = await user_dto.list_and_count(
            self.session,
            query,
            options=(
                selectinload(User.role).load_only(Role.id, Role.name),
                selectinload(User.group).load_only(Group.id, Group.name),
            ),
        )
        return ListResultT(data=ListT(count=count, results=results))

    @router.put("/users/{id}", operation_id="2fda2e00-ad86-4296-a1d4-c7f02366b52e")
    async def update_user(self, id: int, user: schemas.UserUpdate) -> ResultT[IdResponse]:
        update_user = user.model_dump(exclude_unset=True)
        if "password" in update_user and update_user["password"] is None:
            raise GenerError(errors.ERR_10006, status_code=status.HTTP_406_NOT_ACCEPTABLE)
        db_user = await user_dto.get_one_or_404(self.session, id)
        await user_dto.update(self.session, db_user, user)
        return ResultT(data=IdResponse(id=id))

    @router.delete("/users/{id}", operation_id="c4e9e0e8-6b0c-4f6f-9e6c-8d9f9f9f9f9f")
    async def delete_user(self, id: int) -> ResultT[IdResponse]:
        """
        Delete a user from the database.

        Parameters:
            id (int): The ID of the user to be deleted.

        Returns:
            ResultT[IdResponse]: The result of the deletion operation, containing the ID of the deleted user.
        """
        db_user = await user_dto.get_one_or_404(self.session, id)
        await user_dto.delete(self.session, db_user)
        return ResultT(data=IdResponse(id=id))


@cbv(router)
class GroupCbv:
    user: User = Depends(auth)
    session: AsyncSession = Depends(get_session)

    @router.post("/groups", operation_id="e0fe80d5-cbe0-4c2c-9eff-57e80ecba522")
    async def create_group(self, group: schemas.GroupCreate) -> ResultT[IdResponse]:
        """
        Create a new group.

        Args:
            group (schemas.GroupCreate): The group data to create.

        Returns:
            ResultT[int]: The ID of the newly created group.
        """
        if not group.user_ids:
            new_group = await group_dto.create(self.session, group)
        else:
            users = (await self.session.scalars(select(User).where(User.id.in_(group.user_ids)))).all()
            new_group = await group_dto.create_with_users(self.session, group, users)
        return ResultT(data=IdResponse(id=new_group.id))

    @router.get("/groups/{id}", operation_id="8057d614-150f-42ee-984c-d0af35796da3")
    async def get_group(self, id: int) -> ResultT[schemas.GroupDetail]:
        """
        Get a group by its ID.

        Args:
            id (int): The ID of the group.

        Returns:
            GroupDetail: The detailed information of the group.

        Raises:
            HTTPException: If the group with the specified ID is not found.
        """
        db_group = await group_dto.get_one_or_404(self.session, id)
        return ResultT(data=schemas.GroupDetail.model_validate(db_group))

    @router.get("/groups", operation_id="c5f793b1-7adf-4b4e-a498-732b0fa7d758")
    async def get_groups(self, query: schemas.GroupQuery) -> ListResultT[list[schemas.GroupDetail]]:
        """
        Get a list of groups based on the provided query parameters.

        Args:
            query (schemas.GroupQuery): The query parameters to filter the groups.

        Returns:
            ListT[list[schemas.GroupDetail]]: A list of group details matching the query.
        """
        count, results = await group_dto.list_and_count(self.session, query)
        return ListResultT(data=ListT(count=count, results=results))

    @router.put("/groups/{id}", operation_id="2fda2e00-ad86-4296-a1d4-c7f02366b52e")
    async def update_group(self, id: int, group: schemas.GroupUpdate) -> ResultT[IdResponse]:
        """
        Update a group.

        Args:
            id (int): The ID of the group to update.
            group (schemas.GroupUpdate): The updated group data.

        Returns:
            ResultT[IdResponse]: The result of the update operation, containing the ID of the updated group.
        """
        db_group = await group_dto.get_one_or_404(self.session, id, options=(selectinload(Group.user),))
        update_group = group.model_dump(exclude_unset=True)
        if "user_ids" in update_group():
            db_group = group_dto.update_relationship_field(self.session, db_group, User, "user", group.user_ids)
        await group_dto.update(self.session, db_group, group)
        return ResultT(data=IdResponse(id=id))

    @router.delete("/groups/{id}", operation_id="c4e9e0e8-6b0c-4f6f-9e6c-8d9f9f9f9f9f")
    async def delete_group(self, id: int) -> ResultT[IdResponse]:
        """
        Delete a group by its ID.

        Args:
            id (int): The ID of the group to delete.

        Returns:
            ResultT[IdResponse]: The result of the deletion operation, containing the ID of the deleted group.
        """
        db_group = await group_dto.get_one_or_404(self.session, id)
        await group_dto.delete(self.session, db_group)
        return ResultT(data=IdResponse(id=id))
