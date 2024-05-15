from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Generic, TypedDict, TypeVar, overload
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Row, Select, Text, cast, desc, func, inspect, not_, or_, select, text, types
from sqlalchemy.dialects.postgresql import ARRAY, HSTORE, INET, JSON, JSONB, MACADDR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import InstrumentedAttribute, selectinload, undefer
from sqlalchemy.sql.base import ExecutableOption

from src.core._types import Order, QueryParams
from src.core.database.session import async_engine
from src.core.errors.auth_exceptions import ExistError, NotFoundError
from src.core.models.base import Base
from src.core.utils.context import locale_ctx

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import ReflectedForeignKeyConstraint, ReflectedUniqueConstraint

    from src.core.models.mixins import AuditLog

ModelT = TypeVar("ModelT", bound=Base)
PkIdT = TypeVar("PkIdT", int, UUID)
RelationT = TypeVar("RelationT", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
QuerySchemaType = TypeVar("QuerySchemaType", bound=QueryParams)

TABLE_PARAMS: dict[str, "InspectorTableConstraint"] = {}


class InspectorTableConstraint(TypedDict, total=False):
    foreign_keys: dict[str, tuple[str, str]]
    unique_constraints: list[list[str]]


def register_table_params(table_name: str, params: InspectorTableConstraint) -> None:
    if not TABLE_PARAMS.get(table_name):
        TABLE_PARAMS[table_name] = params


async def inspect_table(table_name: str) -> InspectorTableConstraint:
    """Reflect table schema to inspect unique constraints and many-to-one fks and cache in memory"""
    if result := TABLE_PARAMS.get(table_name, None):  # noqa: PGH003 # type: ignore
        return result
    async with async_engine.connect() as conn:
        result: InspectorTableConstraint = {"unique_constraints": [], "foreign_keys": {}}
        uq: list[ReflectedUniqueConstraint] = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_unique_constraints(table_name=table_name)
        )
        if uq:
            result["unique_constraints"] = [_uq["column_names"] for _uq in uq]
        fk: list[ReflectedForeignKeyConstraint] = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_foreign_keys(table_name=table_name)
        )
        if fk:
            for _fk in fk:
                fk_name = _fk["constrained_columns"][0]
                referred_table = _fk["referred_table"]
                referred_column = _fk["referred_columns"][0]
                result["foreign_keys"][fk_name] = (referred_table, referred_column)
        register_table_params(table_name=table_name, params=result)
        return result


class BaseRepository(Generic[ModelT, CreateSchemaType, UpdateSchemaType, QuerySchemaType]):
    id_attribute: str = "id"
    check_nullable: bool = True
    check_unique_constraints: bool = True

    def __init__(self, model: type[ModelT]) -> None:
        """
        Initializes a new instance of the class.

        Args:
            model (type[ModelT]): The model to be used.

        Returns:
            None
        """
        self.model = model

    @overload
    @classmethod
    def get_id_attribute_value(cls, obj: ModelT, id_attribute: str | None = None) -> PkIdT:
        ...

    @overload
    @classmethod
    def get_id_attribute_value(cls, obj: type[ModelT], id_attribute: str | None = None) -> InstrumentedAttribute[PkIdT]:
        ...

    @classmethod
    def get_id_attribute_value(
        cls, obj: ModelT | type[ModelT], id_attribute: str | None = None
    ) -> InstrumentedAttribute[PkIdT] | PkIdT:
        """Get value of attribute named as :attr:`id_attribute` on ``obj``.

        Args:
            item: Anything that should have an attribute named as :attr:`id_attribute` value.
            id_attribute: Allows customization of the unique identifier to use for model fetching.
                Defaults to `None`, but can reference any surrogate or candidate key for the table.

        Returns:
            The value of attribute on ``obj`` named as :attr:`id_attribute <AbstractAsyncRepository.id_attribute>`.
        """
        return getattr(obj, id_attribute if id_attribute is not None else cls.id_attribute)

    def inspect_relationship(self) -> dict[str, type["RelationT"]]:
        result: dict[str, type["RelationT"]] = {}
        insp = inspect(self.model)
        for relationship in insp.relationships:
            key = relationship.key
            direction_name = relationship.direction.name
            if direction_name in ("MANYTOMANY", "ONETOMANY"):
                _class = relationship.mapper.class_
                result[key] = _class
        return result

    def _get_base_stmt(self) -> Select[tuple[ModelT]]:
        """Get base select statement of query"""
        return select(self.model)

    def _get_base_count_stmt(self) -> Select[tuple[int]]:
        """
        Returns a SQLAlchemy select statement that counts the number of rows in the base table of the model.

        :param self: The instance of the class.
        :return: A SQLAlchemy select statement that counts the number of rows.
        :rtype: Select[tuple[ModelT]]
        """
        return select(func.count()).select_from(self.model)

    def _apply_search(self, stmt: Select[tuple[ModelT]], value: str, ignore_case: bool = True) -> Select[tuple[ModelT]]:
        """
        Apply a search filter to the given statement.

        Args:
            stmt (Select[tuple[ModelT]]): The statement to apply the search filter to.
            value (str): The value to search for.
            ignore_case (bool): Whether to ignore case when searching.

        Returns:
            Select[tuple[ModelT]]: The statement with the search filter applied.
        """
        where_clauses = []
        search_text = f"%{value}%"
        casting_types = (HSTORE, JSON, JSONB, INET, MACADDR, ARRAY, types.JSON, types.ARRAY)
        for field in self.model.__search_fields__:
            _t = getattr(self.model, field).type
            if type(_t) in casting_types:
                if ignore_case:
                    where_clauses.append(cast(getattr(self.model, field), Text).ilike(search_text))
                else:
                    where_clauses.append(cast(getattr(self.model, field), Text).like(search_text))
            elif ignore_case:
                where_clauses.append(getattr(self.model, field).ilike(search_text))
            else:
                where_clauses.append(getattr(self.model, field).like(search_text))

        return stmt.where(or_(False, *where_clauses))

    def _apply_order_by(self, stmt: Select[tuple[ModelT]], order_by: str, order: Order) -> Select[tuple[ModelT]]:
        """
        Applies an order by clause to the given SELECT statement.

        Args:
            stmt (Select[tuple[ModelT]]): The SELECT statement to apply the order by clause to.
            order_by (str): The name of the column to order by.
            order (Order): The order to apply, either "ascend" or "descend".

        Returns:
            Select[tuple[ModelT]]: The modified SELECT statement with the order by clause applied.
        """
        return (
            stmt.order_by(desc(getattr(self.model, order_by)))
            if order == "ascend"
            else stmt.order_by(getattr(self.model, order_by))
        )

    def _apply_pagination(self, stmt: Select[tuple[ModelT]], limit: int = 20, offset: int = 0) -> Select[tuple[ModelT]]:
        """
        Apply pagination to the given SQL statement.

        Args:
            stmt (Select[tuple[ModelT]]): The SQL statement to apply pagination to.
            limit (int): The maximum number of rows to return. Defaults to 20.
            offset (int): The number of rows to skip. Defaults to 0.

        Returns:
            Select[tuple[ModelT]]: The paginated SQL statement.
        """
        return stmt.slice(offset, limit + offset)

    def _apply_operator_filter(self, stmt: Select[tuple[ModelT]], key: str, value: Any) -> Select[tuple[ModelT]]:
        """
        Apply an operator filter to the given statement.

        Args:
            stmt (Select[tuple[ModelT]]): The statement to apply the filter to.
            key (str): The key used to determine the field name and operator. \n
            key format should be `field_name__operator`.
            eg: "start_at__lte", "end_at__gt", "name__ic", "name__nic"
            value (Any): The value used for the filter.
            support:
                eq: equal, accepts list of values
                ne: not equal, accepts list of values
                ic: ignore case
                nic: not ignore case
                le: less than equal
                ge: greater than equal
                lte: less than
                gte: greater than
                sw: starts with
                nsw: not starts with
                ew: ends with
                new: not ends with

        Returns:
            Select[tuple[ModelT]]: The filtered statement.
        """
        operators = {
            "eq": lambda col, value: col.in_(value if isinstance(value, list) else [value]),
            "ne": lambda col, value: ~col.in_(value if isinstance(value, list) else [value]),
            "ic": lambda col, value: col.ilike(f"%{value}%"),
            "nic": lambda col, value: not_(col.ilike(f"%{value}%")),
            "le": lambda col, value: col < value,
            "ge": lambda col, value: col > value,
            "lte": lambda col, value: col <= value,
            "gte": lambda col, value: col >= value,
            "sw": lambda col, value: col.like(f"{value}%"),
            "nsw": lambda col, value: not_(col.like(f"{value}%")),
            "ew": lambda col, value: col.like(f"%{value}"),
            "new": lambda col, value: not_(col.like(f"%{value}%")),
        }

        field_name, operator = key.split("__")
        if not hasattr(self.model, field_name):
            return stmt

        operator_func = operators.get(operator)
        if operator_func:
            col = getattr(self.model, field_name)
            return stmt.filter(operator_func(col, value))

        return stmt

    def _apply_filter(self, stmt: Select[tuple[ModelT]], filters: dict[str, Any]) -> Select[tuple[ModelT]]:
        """
        Apply filters to a SQLAlchemy select statement.

        Args:
            stmt (Select[tuple[ModelT]]): The SQLAlchemy select statement to apply filters to.
            filters (dict[str, Any]): The filters to apply to the select statement.

        Returns:
            Select[tuple[ModelT]]: The modified select statement with filters applied.
        """
        for key, value in filters.items():
            if "__" in key:
                stmt = self._apply_operator_filter(stmt, key, value)
            elif isinstance(value, bool):
                stmt = stmt.where(getattr(self.model, key).is_(value))
            elif isinstance(value, list):
                if value:
                    if key in self.model.__i18n_fields__ and type(getattr(self.model, key).type) is types.JSON:
                        stmt = stmt.where(
                            or_(
                                getattr(self.model, key)["zh_CN"].in_(value),
                                getattr(self.model, key)["en_US"].in_(value),
                            )
                        )
                    else:
                        stmt = stmt.where(getattr(self.model, key).in_(value))
            elif value is None:
                stmt = stmt.where(getattr(self.model, key).is_(None))
            else:
                stmt = stmt.where(getattr(self.model, key) == value)
        return stmt

    def _apply_selectinload(
        self, stmt: Select[tuple[ModelT]], *options: ExecutableOption, undefer_load: bool = True
    ) -> Select[tuple[ModelT]]:
        """
        Apply the selectinload option to a SQLAlchemy select statement.

        Args:
            stmt (Select[tuple[ModelT]]): The select statement to apply the selectinload option to.
            options (tuple[ExecutableOption] | None, optional): The additional options to apply to the statement.
            undefer_load: (bool, optional): Whether to apply the undefer load option. Defaults to True.
            if True, all `column_property` defined in the model will be executed in subquery. when set to `False`
            all `column_property` defined in the model will not execute for better performance.
        Returns:
            Select[tuple[ModelT]]: The modified select statement.

        """
        stmt = stmt.options(*options) if options else stmt
        return stmt.options(undefer("*")) if undefer_load else stmt

    def _apply_list(
        self, stmt: Select[tuple[ModelT]], query: QuerySchemaType, excludes: set[str] | None = None
    ) -> Select[tuple[ModelT]]:
        _excludes = {"limit", "offset", "q", "order", "order_by"}
        if excludes:
            _excludes.update(excludes)
        filters = query.model_dump(exclude=_excludes, exclude_unset=True)
        if filters:
            stmt = self._apply_filter(stmt, filters)
        return stmt

    @overload
    def _check_not_found(self, instance: ModelT | None, column: str, value: Any) -> ModelT:
        ...

    @overload
    def _check_not_found(self, instance: Row[Any] | None, column: str, value: Any) -> Row[Any]:
        ...

    def _check_not_found(self, instance: ModelT | Row[Any] | None, column: str, value: Any) -> ModelT | Row[Any]:
        """
        Check if the given instance is not found in the specified table.

        Parameters:
            instance (ModelT | Row[Any] | None): The instance to check.
            table_name (str): The name of the table.
            column (str): The name of the column.
            value (Any): The value to search for.

        Returns:
            None

        Raises:
            NotFoundError: If the instance is not found.
        """
        if not instance:
            raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], column, value)
        return instance

    def _check_exist(self, instance: ModelT | int | None, column: str, value: Any) -> None:
        """
        Check if the given instance exists in the table.

        Args:
            instance (ModelT | None): The instance to check.
            table_name (str): The name of the table.
            column (str): The column to check.
            value (Any): The value to check.

        Returns:
            None: This function does not return anything.

        Raises:
            ExistError: If the instance exists in the table.

        """
        if instance:
            raise ExistError(self.model.__visible_name__[locale_ctx.get()], column, value)

    @staticmethod
    def _update_mutable_tracking(
        update_schema: UpdateSchemaType, obj: ModelT, excludes: set[str] | None = None
    ) -> ModelT:
        """
        Updates the mutable attributes of the given object `obj` based on the provided `update_schema`.

        Parameters:
            update_schema (UpdateSchemaType): The schema containing the updates to be applied.
            obj (ModelT): The object to be updated.
            excludes (set[str]): A set of attributes to be excluded from the update process.

        Returns:
            ModelT: The updated object.

        Description:
            This static method updates the mutable attributes of the given object `obj`
            based on the provided `update_schema`. The `update_schema` is an instance
            of the `UpdateSchemaType`, which defines a schema for updating the object.
            The method iterates over the key-value pairs in the `update_schema` and
            applies the updates to the corresponding attributes of the `obj`.

            If the attribute is an instance of a subclass of `Mutable`, the method
            creates a copy of the attribute and applies the updates to the copy. If the
            updated value is a dictionary or a list, the method updates the attribute
            with the new value. If the updated value is a dictionary, the method updates
            the corresponding key-value pairs in the attribute's copy. Finally, if the
            attribute is not an instance of a subclass of `Mutable`, the method directly
            updates the attribute with the new value.

            The method returns the updated object `obj`.

        Precondition:
            - The `excludes` set should only contain attribute names that exist in the
              `update_schema`.

        Postcondition:
            - The object `obj` is updated according to the `update_schema`.
            - The attributes in `excludes` are not updated.
        """
        for key, value in update_schema.model_dump(exclude_unset=True, exclude=excludes).items():
            if issubclass(type(getattr(obj, key)), Mutable):
                field_value = getattr(obj, key).copy()
                if isinstance(value, dict | list):
                    if isinstance(value, list):
                        setattr(obj, key, value)
                    else:
                        for k, v in value.items():
                            field_value[k] = v
                        setattr(obj, key, field_value)
            else:
                setattr(obj, key, value)
        return obj

    async def _check_unique_constraints(
        self,
        session: AsyncSession,
        uq: dict[str, Any],
        pk_id: PkIdT | None = None,
    ) -> None:
        """
        Check the unique constraints of the model in the database.

        Args:
            session (AsyncSession): The database session to use.
            uq (dict[str, Any]): A dictionary representing the unique constraints to check.
            pk_id (int | None, optional): The primary key ID of the model instance to exclude from the check.
            pk_id should be provided if used to update an existing model, obj self will not be checked anymore

        Raises:
            ExistError: If any of the unique constraints are violated.

        Returns:
            None: This function does not return anything.
        """
        stmt = self._get_base_count_stmt()
        id_str = self.get_id_attribute_value(self.model)
        if pk_id:
            stmt = stmt.where(id_str != pk_id)

        for key, value in uq.items():
            if isinstance(value, bool):
                stmt = stmt.where(getattr(self.model, key).is_(value))
            else:
                stmt = stmt.where(getattr(self.model, key) == value)

        result = await session.scalar(stmt)
        if result is not None and result > 0:
            keys = ",".join(uq.keys())
            values = ",".join([f"{key}-{value}" for key, value in uq.items()])
            raise ExistError(self.model.__visible_name__[locale_ctx.get()], keys, values)

    async def _apply_unique_constraints_when_create(
        self,
        session: AsyncSession,
        record: CreateSchemaType,
        inspections: InspectorTableConstraint,
    ) -> None:
        """Apply unique constraints of given object in database.

        Args:
            session (AsyncSession): sqla session
            record (CreateSchemaType)
            inspections (InspectorTableConstraint)
        """
        uniq_args = inspections.get("unique_constraints")
        if not uniq_args:
            return
        record_dict = record.model_dump(exclude_unset=True)
        for arg in uniq_args:
            uq: dict[str, Any] = {}
            # Check if all columns in the constraint exist in the record dictionary
            for column in arg:
                if column in record_dict:
                    if record_dict[column]:
                        uq[column] = record_dict[column]
                    else:
                        uq = {}
                        break
                else:
                    uq = {}
                    break
            if uq:
                await self._check_unique_constraints(session, uq)

    async def _apply_unique_constraints_when_update(
        self, session: AsyncSession, record: UpdateSchemaType, inspections: InspectorTableConstraint, obj: ModelT
    ) -> None:
        """
        Applies unique constraints when updating a record.

        Args:
            session (AsyncSession): The asynchronous session used for the database transaction.
            record (UpdateSchemaType): The record to be updated.
            inspections (InspectorTableConstraint): The table constraints to be inspected.
            obj (ModelT): The model object.

        Returns:
            None: This function does not return anything.
        """
        uniq_args = inspections.get("unique_constraints")
        if not uniq_args:
            return
        record_dict = record.model_dump(exclude_unset=True)
        for arg in uniq_args:
            uq: dict[str, Any] = {}
            for column in arg:
                if column in record_dict:
                    value = record_dict.get(column) or getattr(obj, column)
                    if value is not None:
                        uq[column] = value
                    else:
                        uq = {}
                        break
                elif value := getattr(obj, column):
                    uq[column] = value
                else:
                    uq = {}
                    break
            if uq:
                id_field = self.get_id_attribute_value(obj)
                await self._check_unique_constraints(session, uq, id_field)

    async def _apply_foreign_keys_check(
        self, session: AsyncSession, record: CreateSchemaType | UpdateSchemaType, inspections: InspectorTableConstraint
    ) -> None:
        """
        Apply foreign key checks for the given session, record, and inspections.

        Args:
            session (AsyncSession): The database session.
            record (CreateSchemaType | UpdateSchemaType): The record to apply foreign key checks to.
            inspections (InspectorTableConstraint): The inspections containing foreign key information.

        Returns:
            None: This function does not return anything.
        """
        fk_args = inspections.get("foreign_keys")
        if not fk_args:
            return
        record_dict = record.model_dump()
        for fk_name, relation in fk_args.items():
            if value := record_dict.get(fk_name):
                table_name, column = relation
                stmt_text = f"SELECT 1 FROM {table_name} WHERE {column}='{value}'"  # noqa: S608
                fk_result = (await session.execute(text(stmt_text))).one_or_none()
                self._check_not_found(fk_result, column, value)

    async def create(
        self,
        session: AsyncSession,
        obj_in: CreateSchemaType,
        excludes: set[str] | None = None,
        exclude_unset: bool = False,
        exclude_none: bool = False,
        commit: bool | None = True,
    ) -> ModelT:
        """
        Creates a new object in the database.

        Parameters:
            session (AsyncSession): The database session.
            obj_in (CreateSchemaType): The input object for creating a new record.
            excludes (set[str] | None, optional): A set of fields to exclude from the model dump. Defaults to None.
            commit (bool | None, optional): Whether to commit the changes to the database. Defaults to True.

        Returns:
            ModelT: The newly created object.

        Raises:
            None
        """
        if any((self.check_nullable, self.check_unique_constraints)):
            insp = await inspect_table(self.model.__tablename__)
            if self.check_nullable:
                await self._apply_foreign_keys_check(session, obj_in, insp)
            if self.check_unique_constraints:
                await self._apply_unique_constraints_when_create(session, obj_in, insp)
        m2m = self.inspect_relationship()
        extra_excluded = set(m2m.keys())
        if excludes:
            excludes.update(extra_excluded)
        else:
            excludes = extra_excluded
        new_obj = self.model(
            **obj_in.model_dump(exclude_unset=exclude_unset, exclude_none=exclude_none, exclude=excludes)
        )
        if m2m:
            for key, value in m2m.items():
                if hasattr(obj_in, key) and getattr(obj_in, key) is not None:
                    dto_m2m = BaseRepository(value)
                    db_m2m = await dto_m2m.get_multi_by_pks_or_404(session, [r.id for r in getattr(obj_in, key)])
                    setattr(new_obj, key, db_m2m)
                setattr(obj_in, key, value)
        if commit:
            return await self.commit(session, new_obj)
        return new_obj

    async def update(
        self,
        session: AsyncSession,
        db_obj: ModelT,
        obj_in: UpdateSchemaType,
        excludes: set[str] | None = None,
        commit: bool | None = True,
    ) -> ModelT:
        """
        Update a database object.

        Args:
            session (AsyncSession): The database session.
            db_obj (ModelT): The database object to update.
            obj_in (UpdateSchemaType): The updated data for the object.
            excludes (set | None, optional): The fields to exclude from the update. Defaults to None.
            commit (bool | None, optional): Whether to commit the changes. Defaults to True.

        Returns:
            ModelT: The updated database object.
        """
        if any((self.check_nullable, self.check_unique_constraints)):
            insp = await inspect_table(self.model.__tablename__)
            if self.check_nullable:
                await self._apply_foreign_keys_check(session, obj_in, insp)
            if self.check_unique_constraints:
                await self._apply_unique_constraints_when_update(session, obj_in, insp, db_obj)
        m2m = self.inspect_relationship()
        extra_excluded = set(m2m.keys())
        if excludes:
            excludes.update(extra_excluded)
        else:
            excludes = extra_excluded
        if m2m:
            for key, value in m2m.items():
                if hasattr(obj_in, key) and getattr(obj_in, key) is not None:
                    await self.update_relationship_field(
                        session, db_obj, value, key, [r.id for r in getattr(obj_in, key)], self.id_attribute
                    )
        db_obj = self._update_mutable_tracking(obj_in, db_obj, excludes)
        if commit:
            return await self.commit(session, db_obj)
        return db_obj

    async def update_relationship_field(
        self,
        session: AsyncSession,
        obj: ModelT,
        m2m_model: type[RelationT],
        relationship_name: str,
        fk_values: Sequence[PkIdT] | None,
        relationship_pk_name: str = id_attribute,
    ) -> ModelT:
        """
        Updates a relationship field in the specified object.

        Args:
            session (AsyncSession): The async session object.
            obj (ModelT): The object to update the relationship field for.
            m2m_model (type[RelationT]): The type of the many-to-many or one-to-many relationship model.
            relationship_name (str): The name of the relationship field.
            fk_values (Sequence[PkIdT]): The list of foreign key values to update.

        Returns:
            ModelT: The updated object.

        Raises:
            NotFoundError: If the target object is not found in the many-to-many relationship model.
        """
        local_relationship_values: Sequence[RelationT] = getattr(obj, relationship_name)
        local_fk_value_ids: list[PkIdT] = [getattr(v, relationship_pk_name) for v in local_relationship_values]
        if fk_values:
            for fk_value in local_relationship_values[::-1]:
                if getattr(fk_value, relationship_pk_name) not in fk_values:
                    getattr(obj, relationship_name).remove(fk_value)
            for fk_value in fk_values:
                target_dto = BaseRepository(model=m2m_model)
                if fk_value not in local_fk_value_ids:
                    target_obj = await target_dto.get_one_or_404(session, fk_value)
                    getattr(obj, relationship_name).append(target_obj)
        else:
            setattr(obj, relationship_name, None)
        return obj

    async def list_and_count(
        self, session: AsyncSession, query: QuerySchemaType, *options: ExecutableOption, undefer_load: bool = True
    ) -> tuple[int, Sequence[ModelT]]:
        """
        Asynchronously retrieves a list of items from the database and returns the count and results.

        Args:
            session (AsyncSession): The async session object for the database connection.
            query (QuerySchemaType): The query schema object containing the query parameters.
            options (tuple | None, optional): Additional options for the query. Defaults to None.
            undefer_load (bool, optional): Whether to undefer the load. Defaults to True.
        Returns:
            tuple[int, Sequence[ModelT]]: A tuple containing the count of items and the list of results.
        """
        stmt = self._get_base_stmt()
        stmt = self._apply_list(stmt, query)
        if query.q:
            stmt = self._apply_search(stmt, query.q)
        c_stmt = stmt.with_only_columns(func.count()).order_by(None)
        if query.limit is not None and query.offset is not None:
            stmt = self._apply_pagination(stmt, query.limit, query.offset)
        if query.order_by and query.order:
            stmt = self._apply_order_by(stmt, query.order_by, query.order)
        stmt = self._apply_selectinload(stmt, *options, undefer_load=undefer_load)
        _count = await session.scalar(c_stmt)
        results = (await session.scalars(stmt)).all()
        return _count if _count is not None else 0, results

    async def get_all(self, session: AsyncSession) -> Sequence[ModelT]:
        return (await session.scalars(self._get_base_stmt())).all()

    async def get_one_by_id(
        self, session: AsyncSession, pk_id: PkIdT, *options: ExecutableOption, undefer_load: bool = False
    ) -> ModelT | None:
        """
        Retrieves a single instance of ModelT from the database based on the provided \n
        primary key (pk_id) and optional query options (options).

        Parameters:
            session (AsyncSession): The asynchronous session used to execute the database query.
            pk_id (PkIdT): The primary key value used to identify the instance to be retrieved.
            *options ExecutableOption: query options to apply to the database query.
            undefer_load (bool, optional): Whether to undefer the load. Defaults to False.

        Returns:
            ModelT: The retrieved instance of ModelT from the database.
        """
        stmt = self._get_base_stmt()
        id_str = self.get_id_attribute_value(self.model)
        stmt = stmt.where(id_str == pk_id)
        if options:
            stmt = self._apply_selectinload(stmt, *options, undefer_load=undefer_load)
        return (await session.scalars(stmt)).one_or_none()

    async def get_one_or_404(
        self, session: AsyncSession, pk_id: PkIdT, *options: ExecutableOption, undefer_load: bool = False
    ) -> ModelT:
        """
        Retrieves a single instance of ModelT from the database based on the provided \n
        primary key (pk_id) and optional query options (options).

        Parameters:
            session (AsyncSession): The asynchronous session used to execute the database query.
            pk_id (PkIdT): The primary key value used to identify the instance to be retrieved.
            *options ExecutableOption: query options to apply to the database query.
            undefer_load (bool, optional): Whether to undefer the load. Defaults to False.

        Returns:
            ModelT: The retrieved instance of ModelT from the database.

        Raises:
            NotFoundError: If no instance with the given primary key (pk_id) is found in the database.
        """
        result = await self.get_one_by_id(session, pk_id, *options, undefer_load=undefer_load)
        if not result:
            raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], self.id_attribute, pk_id)
        return result

    async def get_none_or_409(self, session: AsyncSession, field: str, value: Any) -> None:
        """
        Check if a record with the given value exists in the database for the specified field.

        Parameters:
            session (AsyncSession): The asynchronous session used to execute the database query.
            field (str): The name of the field to check.
            value (Any): The value to check for existence.

        Returns:
            None

        Raises:
            ExistError: If a record with the given value already exists in the database.
        """

        stmt = self._get_base_stmt()
        stmt = self._apply_filter(stmt=stmt, filters={field: value})
        result = await session.scalar(stmt)
        self._check_exist(result, field, value)

    async def get_one_by_filter(
        self, session: AsyncSession, filters: dict[str, Any], *options: ExecutableOption, undefer_load: bool = False
    ) -> ModelT | None:
        """
        Retrieves a single instance of the model that matches the given filters.

        Args:
            session (AsyncSession): The async session to be used for the database operations.
            filters (dict[str, Any]): The filters to be applied to the query.
            *options (ExecutableOption): Additional options to be applied to the query.
            undefer_load (bool, optional): Whether to undefer any deferred attributes. Defaults to False.

        Returns:
            ModelT | None: The retrieved model instance, or None if no match is found.
        """
        stmt = self._get_base_stmt()
        stmt = self._apply_filter(stmt=stmt, filters=filters)
        stmt = self._apply_selectinload(stmt, *options, undefer_load=undefer_load)
        return (await session.scalars(stmt)).one_or_none()

    async def get_multi_by_filter(
        self, session: AsyncSession, filters: dict[str, Any], *options: ExecutableOption, undefer_load: bool = False
    ) -> Sequence[ModelT]:
        """
        Retrieves multiple instances of ModelT from the database based on the provided filters.

        Args:
            session (AsyncSession): The active database session.
            filters (dict[str, Any]): A dictionary containing the filters to apply when querying the database.
            *options (ExecutableOption): Variable length argument list of options to customize the query.
            undefer_load (bool, optional): If True, the query will include deferred attributes. Defaults to False.

        Returns:
            Sequence[ModelT]: A sequence of ModelT instances that match the provided filters.
        """
        stmt = self._get_base_stmt()
        stmt = self._apply_filter(stmt=stmt, filters=filters)
        stmt = self._apply_selectinload(stmt, *options, undefer_load=undefer_load)
        return (await session.scalars(stmt)).all()

    async def get_multi_by_ids(
        self, session: AsyncSession, pk_ids: list[PkIdT], *options: ExecutableOption, undefer_load: bool = False
    ) -> Sequence[ModelT]:
        stmt = self._get_base_stmt()
        id_str = self.get_id_attribute_value(self.model)
        stmt = stmt.where(id_str.in_(pk_ids))
        if options:
            stmt = self._apply_selectinload(stmt, *options, undefer_load=undefer_load)
        return (await session.scalars(stmt)).all()

    async def get_multi_by_pks_or_404(
        self, session: AsyncSession, pk_ids: list[PkIdT], *options: ExecutableOption, undefer_load: bool = False
    ) -> Sequence[ModelT]:
        """
        Retrieves multiple records from the database based on a list of primary key IDs.

        Args:
            session (AsyncSession): The database session.
            pk_ids (list[PkIdT]): A list of primary key IDs.
            *options (ExecutableOption): Optional query options.
            undefer_load (bool): Whether to undefer any deferred attributes.

        Returns:
            Sequence[ModelT]: A sequence of model instances.

        Raises:
            NotFoundError: If no records are found with the given primary key IDs.
        """
        results = await self.get_multi_by_ids(session, pk_ids, *options, undefer_load=undefer_load)
        if not results:
            raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], self.id_attribute, pk_ids)
        for r in results:
            id_value = self.get_id_attribute_value(r)
            if id_value not in pk_ids:
                raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], self.id_attribute, pk_ids)
        return results

    async def get_one_and_delete(self, session: AsyncSession, pk_id: PkIdT) -> None:
        """
        Retrieves a single record from the database using the specified primary key ID and deletes it.

        Args:
            session (AsyncSession): The async session object used to interact with the database.
            pk_id (PkIdT): The primary key ID of the record to retrieve and delete.

        Returns:
            None: This function does not return anything.
        """
        result = await self.get_one_or_404(session, pk_id)
        await self.delete(session, result)

    async def get_multi_and_delete(self, session: AsyncSession, pk_ids: list[PkIdT]) -> None:
        """
        Get multiple records by their primary keys and delete them from the database.

        Args:
            session (AsyncSession): The asynchronous session to use for the database operations.
            pk_ids (list[PkIdT]): A list of primary key IDs for the records to retrieve and delete.

        Returns:
            None: This function does not return anything.

        Raises:
            NotFoundError: If any of the primary key IDs are not found in the database.

        """
        results = await self.get_multi_by_ids(session, pk_ids)
        for r in results:
            id_value = self.get_id_attribute_value(r)
            if id_value not in pk_ids:
                raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], self.id_attribute, id_value)
            await session.delete(r)
        await session.commit()

    async def commit(self, session: AsyncSession, obj: ModelT, refresh: bool = False) -> ModelT:
        """
        Commits the changes made in the session and refreshes the given object.

        Args:
            session (AsyncSession): The session used to commit the changes.
            obj (ModelT): The object to be refreshed after the commit.
            refresh (bool, optional): Whether to refresh the object. Defaults to False.

        Returns:
            ModelT: The creating/updating object.
        """
        """"""
        session.add(obj)
        await session.commit()
        if refresh:
            await session.refresh(obj)
        return obj

    async def batch_commit(self, session: AsyncSession, objs: list[ModelT], refresh: bool = False) -> list[ModelT]:
        """
        Commits the changes made in the session and refreshes the given objects.

        Args:
            session (AsyncSession): The session used to commit the changes.
            objs (Sequence[ModelT]): The objects to be refreshed after the commit.
            refresh (bool, optional): Whether to refresh the object. Defaults to False.

        Returns:
            None
        """
        """"""
        session.add_all(objs)
        await session.commit()
        if refresh:
            for obj in objs:
                await session.refresh(obj)
        return objs

    async def delete(self, session: AsyncSession, db_obj: ModelT) -> None:
        """
        Delete a database object.

        Args:
            session (AsyncSession): The database session.
            db_obj (ModelT): The object to be deleted from the database.

        Returns:
            None
        """
        await session.delete(db_obj)
        await session.commit()

    async def get_audit_log(self, session: AsyncSession, pk_id: PkIdT) -> tuple[int, Sequence["AuditLog"] | None]:
        if hasattr(self.model, "audit_log"):
            stmt = self._get_base_stmt()
            id_str = self.get_id_attribute_value(self.model)
            stmt = stmt.where(id_str == pk_id).options(
                selectinload(self.model.audit_log)  # type: ignore  # noqa: PGH003
            )
            results = (await session.scalars(stmt)).one_or_none()
            if results:
                return len(results.audit_log), results.audit_log  # type: ignore  # noqa: PGH003
            return 0, None
        return 0, None
