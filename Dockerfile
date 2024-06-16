FROM python:3.12-slim-bullseye as base

FROM base AS install

WORKDIR /home/app
ENV PYTHONPATH=/home/app PYTHONHASHSEED=0


COPY alembic.ini .env requirements.lock pyproject.toml README.md ./
COPY src/ src/
COPY alembic/ alembic/
RUN chmod 755 .env
RUN PYTHONDONTWRITEBYTECODE=1 pip install -r requirements.lock
RUN alembic upgrade head

CMD ["python", "src/__main__.py"]
