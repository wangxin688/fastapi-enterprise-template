from typing import Any

from fastapi import FastAPI

from src.app import app
from src.core.config import settings
from src.loggers import LOGGING, configure_logger


def gunicorn_options() -> dict[str, Any]:
    from gunicorn import glogging

    class GunicornLogger(glogging.Logger):
        def setup(self, cfg: Any) -> None:  # noqa: ARG002
            configure_logger()

    return {
        "bind": f"{settings.LISTENING_HOST}:{settings.LISTENING_PORT}",
        "workers": settings.WORKERS,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "preload": "-",
        "forwarded_allow_ips": "*",
        "accesslog": "-",
        "errorlog": "-",
        "logger_class": GunicornLogger,
    }


if __name__ == "__main__":
    if settings.RUNNING_MODE == "uvicorn":
        import uvicorn

        uvicorn.run(
            app,
            host=settings.LISTENING_HOST,
            port=settings.LISTENING_PORT,
            log_config=LOGGING,
            proxy_headers=True,
            forwarded_allow_ips="*",
            loop="uvloop",
            http="httptools",
        )

    else:
        from gunicorn.app.base import BaseApplication

        class StandaloneApplication(BaseApplication):
            def __init__(self, app: FastAPI, options: dict | None = None) -> None:
                self.options = options or {}
                self.application: FastAPI = app
                super().__init__()

            def load_config(self) -> None:
                assert self.cfg is not None  # noqa: S101
                # Filter out options that are not recognized by gunicorn
                filtered_options = {key: value for key, value in self.options.items() if key in self.cfg.settings}

                # Set the filtered options
                for key, value in filtered_options.items():
                    self.cfg.set(key.lower(), value)

            def load(self) -> FastAPI:
                return self.application

        StandaloneApplication(app, gunicorn_options()).run()
