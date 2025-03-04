import time
import uuid
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.core.utils.context import locale_ctx, request_id_ctx


@dataclass
class RequestMiddleware(BaseHTTPMiddleware):
    app: ASGIApp
    csv_mime: str = "text/csv"
    time_header = "x-request-time"
    id_header = "x-request-id"

    async def dispatch_func(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
        locale_ctx.set(request.headers.get(locale_ctx.name, locale_ctx.get()))
        response = await call_next(request)
        response.headers[self.id_header] = request_id
        response.headers[self.time_header] = str(time.time() - start_time)

        return response
