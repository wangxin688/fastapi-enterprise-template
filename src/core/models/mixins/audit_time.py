from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.types import DateTimeTZ

if TYPE_CHECKING:
    from datetime import datetime


class AuditTimeMixin:
    created_at: Mapped["datetime"] = mapped_column(DateTimeTZ, default=func.now(), index=True)
    updated_at: Mapped["datetime"] = mapped_column(DateTimeTZ, default=func.now(), onupdate=func.now())
