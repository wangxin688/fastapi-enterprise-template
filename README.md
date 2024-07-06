# FastAPI enterprise backend template
> fastapi+async sqlalchemy, support both mysql/postgres/sqlite backed, use postgresql as default.

## Features
- [x] Template repository
- [x] Class-based view decrator for better code structure and reduce the duplicated code.
- [x] Sqlalchemy 2.0 with asyncpg integration, with well type annotations and autocompletion support.
- [x] Generic CRUD repository class for very easy and fast restapi development, provide good support for type hint and user friendly error message for database.
- [x] Create and apply almebic migration
- [x] Jwt authentication with access token and refresh token.
- [x] Run app with Uvicorn/Gunicorn with well tuned configuration
- [x] Rye for python package and dependencies management.
- [x] Unified error message and format management
- [x] pre-commit hooks/ruff/typo for static code check
- [x] Basic user/group/role management with crud api.
- [x] Flexible RBAC management
- [x] x-request-id/x-request-time middleware
- [x] x-request-id in log message for tracing
- [x] sqlalchemy costom types and mixins: GUID/EncryptString/AuditLogMixin
- [x] I18N support
- [x] dockerfile and docker-compose support

## QuickStart

### 1. Create repository from a template
See [docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).

### 2. Install dependencies with [Rye](https://rye.astral.sh/guide/installation/)
```bash
cd your_project_name
rye sync
```
Note, be sure to use `python3.12` with this template with either rye or standard venv & pip, if you need to stick to some earlier python version, you should adapt it yourself (change `.python-version` to the version you want and update `pyproject.toml requires-python = "<= 3.x"`)

### 3. Setup .env and database
```bash
### Setup env, change the ENV as you need
mv .env.example .env
### Setup database
docker-compose up -d

### Run Alembic migrations
alembic upgrade head
```

### 4. Now you can run app

```bash
### And this is it:
python3 src/__main__.py
### or run app directly as you wish
uvicorn src.app:app --reload
```

You should then use `git init` (if needed) to initialize git repository and access OpenAPI spec at http://localhost:8000/ by default. To customize docs url, cors and allowed hosts settings,
see `src/core/config.py` options

### 5. Activate pre-commit

[pre-commit](https://pre-commit.com/) is de facto standard now for pre push activities like isort or black or its nowadays replacement ruff.

Refer to `.pre-commit-config.yaml` file to see my current opinionated choices.

```bash
# Install pre-commit
pre-commit install --install-hooks

# Run on all files
pre-commit run --all-files
```

### 6. Running tests

Note, it will create databases for session and run tests in many processes by default (using pytest-xdist) to speed up execution, based on how many CPU are available in environment.

For more details about initial database setup, see logic `tests/conftest.py` file, `fixture_setup_new_test_database` function.



```bash
# see all pytest configuration flags in pyproject.toml
pytest
```

# Project structures
```
src/
├── __init__.py
├── __main__.py                             # uvicorn/gunicorn start entry
├── app.py                                  # fastapi app
├── core
│   ├── __init__.py
│   ├── _types.py                           # project reusable types
│   ├── config.py                           # project configuration files
│   ├── database                            # database utils
│   │   ├── __init__.py
│   │   ├── engine.py                       # sqlalchemy engine configuration
│   │   ├── session.py                      # sqlalchemy async session
│   │   └── types                           # sqlalchemy custom types
│   │       ├── __init__.py
│   │       ├── annotated.py
│   │       ├── datetime.py
│   │       ├── encrypted_string.py
│   │       ├── enum.py
│   │       └── guid.py
│   ├── errors                              # unified errors
│   │   ├── __init__.py
│   │   ├── _error.py
│   │   ├── auth_exceptions.py
│   │   └── base_exceptions.py
│   ├── models                              # ORM model
│   │   ├── __init__.py
│   │   ├── base.py                         # sqlalchemy ORM Base
│   │   └── mixins                          # sqlalchemy mixins
│   │       ├── __init__.py
│   │       ├── audit_log.py
│   │       ├── audit_time.py
│   │       └── audit_user.py
│   ├── repositories                        # Sqlachemy db Generic CRUD class, will suite with pydantic model
│   │   ├── __init__.py
│   │   └── repository.py
│   └── utils                               # project utils
│       ├── __init__.py
│       ├── cbv.py
│       ├── context.py
│       ├── i18n.py
│       ├── processors.py
│       ├── singleton.py
│       ├── translations.py
│       └── validators.py
├── deps.py                                 # auth and other fastapi dependencies
├── features                                # features entry, development here
│   └── admin
│       ├── __init__.py
│       ├── api.py
│       ├── consts.py
│       ├── models.py
│       ├── schemas.py
│       ├── security.py
│       ├── services.py
│       └── utils.py
├── libs                                    # external system sdk
│   ├── __init__.py
│   ├── rabbitmq
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── session.py
│   └── redis
│       ├── __init__.py
│       ├── cache.py
│       ├── rate_limiter.py
│       └── redis.py
├── loggers.py
├── openapi.py
├── py.typed
└── register
    ├── __init__.py
    ├── middlewares.py
    └── routers.py
tests/                                      # pytest entry
├── __init__.py
├── admin
│   └── __init__.py
├── conftest.py
├── factories.py
└── test_01_main.py
```

# Step by step examples
---
> I will show you a example to write a crud api to create a Book with Author and Publisher
> to show one-to-many and many-to-many cases.
> add a new app to `src/features` is recommend directory for business logic.

- `POST` endpoint for create a new object
- `PUT` endpoint for update object
- `GET` endponit for get object
- `DELETE` endpoint for delete object

## Create Sqlalchemy Model
Add `Book` `Author` `Publisher` model to `src/features/books/models.py`.
> Sqlalchemy 2.x is strongly recommend for type annotations. New > style API is very easy to use.
```python3
(...)
from src.core.models.base import Base
from src.core.database.types.annotated import int_pk
from src.core.models.mixins import AuditTimeMixin, AuditLogMixin, AuditUserMixin

class Book(Base, AuditTimeMixin):
    __tablename__ = 'book'
    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(unique=True, index=True)
    author_id: Mapped[int] = mapped_colunm(ForeignKey("author.id", ondelete="CASCADE"))
    author: Mapped["Author"] = relationship(back_populates="book")
    publisher: Mapped[list["Publisher"]] = relationship(
        secondary="book_publisher", back_populates="book"
    )

class Author(Base, AuditLogMixin):
    __tablename__ = "author"
    id: Mapped[int_pk]
    name: Mapped[str]
    books: Mapped[list["Book"]] = relationship(back_populates="author")


class BookPublisher(Base):
    __tablename__ = "book_publisher"
    id: Mapped[int_pk]
    book_id: Mapped[int] = mapped_colunm(ForeignKey("book.id"), primary_key=True)
    publisher_id: Mapped[int] = mapped_colunm(ForeignKey("author.id"), primary_key=True)

class Publisher(Base, AuditUserMixin):
    __tablename__ = "publisher"
    id: Mapped[int_pk]
    name: Mapped[str]
    book: Mapped[list["Book"]] = relationship(
        secondary="book_publisher", back_populates="publisher"
    )

```
## 2. create alembic migration
> import models to `alembic/env.py` first
```
### Use below commands in root folder in virtualenv ###

# if you see FAILED: Target database is not up to date.
# first use alembic upgrade head

# Create migration with alembic revision
alembic revision --autogenerate -m "create_book_model"


# a new version file "xxxx_create_book_model_xxxxx.py" should appear in `/alembic/versions` folder


# Apply migration using alembic upgrade
alembic upgrade head

# (...)
# INFO  [alembic.runtime.migration] Running upgrade xxxxx -> xxxx, create_book_model
```

## 3. create pedantic schema for response and request
```python
(...)
from fastapi import Query

from src.core._types import AuditTime, BaseModel, IdCreate, QueryParams

class BookBase(BaseModel):
    name: str

class BookCreate(BookBase):
    author_id: int | None = None
    publisher: list[IdCreate] | None = None

class BookQuery(QueryParams)
    name: list[str] | None = Field(Query(default=[]))
    created_at__gte: datetime | None = None
    created_at__lte: datetime | None = None

class Book(BookCreate, AuditTime):
    id: int
    author: "Author" | None = None

class AuthorBase(BaseModel):
    name: str
```
