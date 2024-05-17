from contextvars import ContextVar
from uuid import uuid4

request_id_ctx: ContextVar[str] = ContextVar("x-request-id", default=str(uuid4()))
user_ctx: ContextVar[int | None] = ContextVar("x-auth-user", default=None)
locale_ctx: ContextVar[str] = ContextVar("Accept-Language", default="en_US")
orm_diff_ctx: ContextVar[dict | None] = ContextVar("x-orm-diff", default=None)
celery_current_id: ContextVar[str | None] = ContextVar("x-celery-cid", default=None)
celery_parent_id: ContextVar[str | None] = ContextVar("x-celery-pid", default=None)
