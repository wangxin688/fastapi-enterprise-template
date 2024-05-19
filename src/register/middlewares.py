import io
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pandas as pd
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

from src.core.utils.context import locale_ctx, request_id_ctx


@dataclass
class RequestMiddleware(BaseHTTPMiddleware):
    app: ASGIApp
    dispatch_func: Callable = field(init=False)
    csv_mime: str = "text/csv"
    time_header = "x-request-time"
    id_header = "x-request-id"
    content_type: str = "Content-Type"

    def __post_init__(self) -> None:
        self.dispatch_func = self.dispatch

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
        language = request.headers.get(locale_ctx.name, locale_ctx.get())
        locale_ctx.set(language)
        content_type = request.headers.get(self.content_type, None)
        if all((content_type, content_type == self.csv_mime, request.method == "GET")):
            response: StreamingResponse = await call_next(request)
            async for _res in response.body_iterator:
                response_data = _res.decode()
                if response_data:
                    response_data = json.loads(response_data)
                    csv_result = response_data.get("results", [])
                    df = pd.DataFrame(csv_result)
                    output = io.StringIO()
                    df.to_csv(output, encoding="utf-8", index=False)
                    filename = f"exporting_data_{datetime.now(tz=UTC).strftime('%Y%m%d %H%M%S')}.csv"
                    csv_resp = StreamingResponse(iter([output.getvalue()]), media_type="application/otect-stream")
                    csv_resp.headers["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
                    csv_resp.headers[self.id_header] = request_id
                    return csv_resp
        response = await call_next(request)
        response.headers[self.id_header] = request_id
        process_time = str(time.time() - start_time)
        response.headers[self.time_header] = process_time
        return response
