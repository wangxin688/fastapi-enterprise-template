import uuid
from datetime import date, datetime
from typing import Annotated

from sqlalchemy import Boolean, Date, Integer
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import expression

from src.core.database.types.datetime import DateTimeTZ
from src.core.database.types.guid import GUID

uuid_pk = Annotated[uuid.UUID, mapped_column(GUID, default=uuid.uuid4, primary_key=True, index=True, nullable=False)]
int_pk = Annotated[int, mapped_column(Integer, primary_key=True, index=True, nullable=False)]
bool_true = Annotated[bool, mapped_column(Boolean, server_default=expression.true(), nullable=False)]
bool_false = Annotated[bool, mapped_column(Boolean, server_default=expression.false(), nullable=False)]
datetime_required = Annotated[datetime, mapped_column(DateTimeTZ, nullable=False)]
datetime_optional = Annotated[datetime, mapped_column(DateTimeTZ, nullable=True)]
date_required = Annotated[date, mapped_column(Date, nullable=False)]
date_optional = Annotated[date | None, mapped_column(Date, nullable=True)]
