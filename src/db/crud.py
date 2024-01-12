from typing import TypeVar

from src.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
