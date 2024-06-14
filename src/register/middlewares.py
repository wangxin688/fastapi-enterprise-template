import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

from src.core.utils.context import locale_ctx, request_id_ctx
from src.core.utils.processors import export_csv


@dataclass
class RequestMiddleware(BaseHTTPMiddleware):
    app: ASGIApp
    csv_mime: str = "text/csv"
    time_header = "x-request-time"
    id_header = "x-request-id"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
        locale_ctx.set(request.headers.get(locale_ctx.name, locale_ctx.get()))

        response = (
            await self._process_csv_response(request, call_next, request_id, start_time)
            if self._is_csv_response(request)
            else await call_next(request)
        )

        response.headers[self.id_header] = request_id
        response.headers[self.time_header] = str(time.time() - start_time)

        return response

    def _is_csv_response(self, request: Request) -> bool:
        return request.headers.get("Content-Type") == self.csv_mime and request.method == "GET"

    async def _process_csv_response(
        self, request: Request, call_next: RequestResponseEndpoint, request_id: str, start_time: float
    ) -> Response:
        response: StreamingResponse = await call_next(request)  # type: ignore  # noqa: PGH003
        csv_data = await self._read_stream_data(response)
        csv_result = json.loads(csv_data).get("results", [])
        output = export_csv(csv_result)

        csv_resp = StreamingResponse(iter([output]), media_type="application/octet-stream")
        csv_resp.headers.update(
            {
                "Content-Disposition": f'attachment; filename="exporting_data_{datetime.now(tz=UTC).strftime("%Y%m%d %H%M%S")}.csv"',
                self.id_header: request_id,
                self.time_header: str(time.time() - start_time),
            }
        )

        return csv_resp

    async def _read_stream_data(self, response: StreamingResponse) -> str:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        return body.decode()
