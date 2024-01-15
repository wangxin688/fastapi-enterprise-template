from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("x-request-id", default=None)
auth_user_ctx: ContextVar[int | None] = ContextVar("x-auth-user", default=None)
locale_ctx: ContextVar[str | None] = ContextVar("Accept-Language", default="en")
orm_diff_ctx: ContextVar[dict | None] = ContextVar("x-orm-diff", default=None)
celery_current_id: ContextVar[str | None] = ContextVar("x-celery-cid", default=None)
celery_parent_id: ContextVar[str | None] = ContextVar("x-celery-pid", default=None)
