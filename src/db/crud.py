from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Generic, NamedTuple, TypedDict, TypeVar

from pydantic import BaseModel
from sqlalchemy import Row, Select, Text, cast, desc, func, inspect, not_, or_, select, text
from sqlalchemy.dialects.postgresql import ARRAY, HSTORE, INET, JSON, JSONB, MACADDR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import undefer

from src._types import Order, QueryParams
from src.context import locale_ctx
from src.db.base import Base
from src.db.session import async_engine
from src.exceptions import ExistError, NotFoundError

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import ReflectedForeignKeyConstraint, ReflectedUniqueConstraint

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
QuerySchemaType = TypeVar("QuerySchemaType", bound=QueryParams)

TABLE_PARAMS: dict[str, "InspectorTableConstraint"] = {}


class OrmField(NamedTuple):
    field: str
    value: Any


class InspectorTableConstraint(TypedDict, total=False):
    foreign_keys: dict[str, tuple[str, str]]
    unique_constraints: list[list[str]]


def register_table_params(table_name: str, params: InspectorTableConstraint) -> None:
    if not TABLE_PARAMS.get(table_name):
        TABLE_PARAMS[table_name] = params


async def inspect_table(table_name: str) -> dict[str, InspectorTableConstraint]:
    """Reflect table schema to inspect unique constraints and many-to-one fks and cache in memory"""
    if result := TABLE_PARAMS.get(table_name):
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


class DtoBase(Generic[ModelT, CreateSchemaType, UpdateSchemaType, QuerySchemaType]):
    def __init__(self, model: type[ModelT], undefer_load: bool = False) -> None:
        self.model = model
        self.undefer_load = undefer_load

    def _get_base_stmt(self) -> Select[tuple[ModelT]]:
        """Get base select statement of query"""
        return select(self.model)

    def _get_base_count_stmt(self) -> Select[tuple[ModelT]]:
        return select(func.count()).select_from(self.model)

    def _apply_search(self, stmt: Select[tuple[ModelT]], value: str, ignore_case: bool) -> Select[tuple[ModelT]]:
        where_clauses = []
        search_text = f"%{value}%"
        if self.model.__search_fields__:
            for field in self.model.__search_fields__:
                _t = getattr(self.model, field).type
                if type(_t) in (HSTORE, JSON, JSONB, INET, MACADDR, ARRAY):
                    if ignore_case:
                        where_clauses.append(cast(getattr(self.model, field), Text).ilike(search_text))
                    else:
                        where_clauses.append(cast(getattr(self.model, field), Text).like(search_text))
        if where_clauses:
            return stmt.where(or_[False, *where_clauses])
        return stmt

    def _apply_order_by(self, stmt: Select[tuple[ModelT]], order_by: str, order: Order) -> Select[tuple[ModelT]]:
        if order == "ascend":
            return stmt.order_by(desc(getattr(self.model, order_by)))
        return stmt.order_by(getattr(self.model, order_by))

    def _apply_pagination(
        self, stmt: Select[tuple[ModelT]], limit: int | None = 20, offset: int | None = 0
    ) -> Select[tuple[ModelT]]:
        return stmt.slice(offset, limit + offset)

    def _apply_operator_filter(self, stmt: Select[tuple[ModelT]], key: str, value: Any) -> Select[tuple[ModelT]]:
        operators = {
            "eq": lambda col, value: col.in_(value if isinstance(value, list) else [value]),
            "ne": lambda col, value: ~col.in_(value if isinstance(value, list) else [value]),
            "ic": lambda col, value: col.ilike(f"%{value}%"),
            "nic": lambda col, value: not_(col.ilike(f"%{value}%")),
            "le": lambda col, value: col < value,
            "ge": lambda col, value: col > value,
            "lte": lambda col, value: col <= value,
            "gte": lambda col, value: col >= value,
        }
        filed_name, operator = key.split("__")
        if not hasattr(self.model, filed_name):
            return stmt
        if operator_func := operators.get(operator, None):
            col = getattr(self.model, filed_name)
            return stmt.filter(operator_func(col, value))
        return stmt

    def _apply_filter(self, stmt: Select[tuple[ModelT]], filters: dict[str, Any]) -> Select[tuple[ModelT]]:
        for key, value in filters.items():
            if "__" in key:
                stmt = self._apply_operator_filter(stmt, key, value)
            elif isinstance(value, bool):
                stmt = stmt.where(getattr(self.model, key).is_(value))
            elif isinstance(value, list):
                if value:
                    if key == "name" and type(getattr(self.model, key).type) is HSTORE:
                        stmt = stmt.where(or_(self.model.name["zh_CN"].in_(value), self.model.name["en_US"].in_(value)))
                    else:
                        stmt = stmt.where(getattr(self.model, key).in_(value))
                else:
                    stmt = stmt.where(getattr(self.model, key).in_(value))
            elif not value:
                stmt = stmt.where(getattr(self.model, key).is_(None))
            else:
                stmt = stmt.where(getattr(self.model, key) == value)
        return stmt

    def _apply_selectinload(self, stmt: Select[tuple[ModelT]], options: tuple | None = None) -> Select[tuple[ModelT]]:
        if options:
            stmt = stmt.options(*options)
        if self.undefer_load:
            stmt = stmt.options(undefer("*"))
        return stmt

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

    @staticmethod
    def _check_not_found(instance: ModelT | Row[Any] | None, table_name: str, column: str, value: Any) -> None:
        if not instance:
            raise NotFoundError(table_name, column, value)

    @staticmethod
    def _check_exist(instance: ModelT | None, table_name: str, column: str, value: Any) -> None:
        if instance:
            raise ExistError(table_name, column, value)

    @staticmethod
    def _update_mutable_tracking(update_schema: UpdateSchemaType, obj: ModelT, excludes: set[str]) -> ModelT:
        for key, value in update_schema.model_dump(exclude_unset=True, exclude=excludes).items():
            if issubclass(type(getattr(obj, key)), Mutable):
                field_value = getattr(obj, key).copy()
                if isinstance(value, list | dict):
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
        pk_id: int | None = None,
    ) -> None:
        stmt = self._get_base_count_stmt()
        if pk_id:
            stmt = stmt.where(self.model.id != pk_id)
        for key, value in uq.items():
            if isinstance(value, bool):
                stmt = stmt.where(getattr(self.model, key).is_(value))
            else:
                stmt.where(getattr(self.model, key) == value)
        result = await session.scalar(stmt)
        if result > 0:
            keys = ",".join(list[uq.keys()])
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
            for column in arg:
                if column in record_dict:
                    if record_dict.get(column):
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
        uniq_args = inspections.get("unique_constraints")
        if uniq_args:
            record_dict = record.model_dump(exclude_unset=True)
        for arg in uniq_args:
            uq: dict[str, Any] = {}
            for column in arg:
                if column in record_dict:
                    if any([value := record_dict.get(column), value := getattr(obj, column)]):
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
                await self._check_unique_constraints(session, uq, obj.id)

    async def _apply_foreign_keys_check(
        self, session: AsyncSession, record: CreateSchemaType | UpdateSchemaType, inspections: InspectorTableConstraint
    ) -> None:
        fk_args = inspections.get("foreign_keys")
        if not fk_args:
            return
        record_dict = record.model_dump()
        for fk_name, relation in fk_args.items():
            if value := record_dict.get(fk_name):
                table_name, column = relation
                stmt_text = f"SELECT 1 FROM {table_name} WHERE {column}='{value}'"  # noqa: S608
                fk_result = (await session.execute(text(stmt_text))).one_or_none()
                self._check_not_found(fk_result, table_name, column, value)

    async def list_and_count(
        self, session: AsyncSession, query: QuerySchemaType, options: tuple | None = None
    ) -> tuple[int, Sequence[ModelT]]:
        stmt = self._get_base_stmt()
        c_stmt = self._get_base_count_stmt()
        stmt = self._apply_list(stmt, query)
        c_stmt = self._apply_list(c_stmt, query)
        if query.q:
            stmt = self._apply_search(stmt, query.q)
            c_stmt = self._apply_search(c_stmt, query.q)
        if query.limit is not None and query.offset is not None:
            stmt = self._apply_pagination(stmt, query.limit, query.offset)
        if query.order_by and query.order:
            stmt = self._apply_order_by(stmt, query.order_by, query.order)
        stmt = self._apply_selectinload(stmt, options, True)
        count: int = await session.scalar(c_stmt)  # type: ignore  # noqa: PGH003
        results = (await session.scalars(stmt)).all()
        return count, results

    async def create(self, session: AsyncSession, obj_in: CreateSchemaType, excludes: set[str] | None = None) -> ModelT:
        insp = await inspect_table(self.model.__tablename__)
        await self._apply_foreign_keys_check(session, obj_in, insp)
        await self._apply_unique_constraints_when_create(session, obj_in, insp)
        new_obj = self.model(**obj_in.model_dump(exclude_unset=True, exclude=excludes))
        session.add(new_obj)
        await session.commit()
        await session.flush()
        return new_obj

    async def update(
        self, session: AsyncSession, db_obj: ModelT, obj_in: UpdateSchemaType, excludes: set | None = None
    ) -> ModelT:
        insp = await inspect_table(self.model.__tablename__)
        await self._apply_foreign_keys_check(session, obj_in, insp)
        await self._apply_unique_constraints_when_update(session, obj_in, insp, db_obj)
        db_obj = self._update_mutable_tracking(obj_in, db_obj, excludes)
        session.add(db_obj)
        await session.commit()
        return db_obj

    async def update_relationship_field(  # noqa: PLR0913
        self, session: AsyncSession, obj: ModelT, m2m_model: type[ModelT], fk_name: str, fk_values: list[int]
    ) -> ModelT:
        local_fk_values = getattr(obj, fk_name)
        local_fk_value_ids = [v.id for v in local_fk_values]
        for fk_value in local_fk_values[::-1]:
            if fk_value.id not in fk_values:
                getattr(obj, fk_name).remove(fk_value)
        for fk_value in fk_values:
            if fk_value not in local_fk_value_ids:
                target_obj = await session.get(m2m_model, fk_value)
                if not target_obj:
                    raise NotFoundError(m2m_model.__visible_name__[locale_ctx.get()], "id", fk_value)
                getattr(obj, fk_name).append(target_obj)
        return obj

    async def get_one_or_404(self, session: AsyncSession, pk_id: int, options: tuple | None) -> ModelT:
        stmt = self._get_base_stmt()
        if options:
            stmt = self._apply_selectinload(options)
        result = (await session.scalars(stmt)).one_or_none()
        if not result:
            raise NotFoundError(self.model.__visible_name__[locale_ctx.get()], "id", pk_id)
        return result

    async def get_none_or_409(self, session: AsyncSession, field: str, value: Any) -> None:
        stmt = self._get_base_stmt()
        if isinstance(value, bool) or value is None:
            stmt = stmt.where(getattr(self.model).is_(value))
        else:
            stmt = stmt.where(getattr(self.model) == value)
        stmt.with_only_columns(self.model.id)
        result = (await session.execute(stmt)).one_or_none()
        if result:
            raise ExistError(self.model.__visible_name__[locale_ctx.get()], field, value)
