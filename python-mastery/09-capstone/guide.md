# Capstone — Production-Grade Task Manager API

> **Duration:** 2 weeks | The project you put on your portfolio and show in interviews.

---

## 🎯 What "Production-Grade" Means Here

| Concern | What We Build |
|---------|--------------|
| **Code quality** | mypy --strict, ruff, pre-commit hooks |
| **Testing** | Unit + integration + E2E, 90 %+ coverage, async test DB |
| **Security** | Argon2 passwords, JWT (access + refresh), rate limiting, CORS, security headers |
| **Observability** | Structured JSON logs (structlog), Prometheus metrics, `/health` with DB ping |
| **Reliability** | Alembic migrations, graceful shutdown, connection pooling, retries |
| **Developer UX** | Docker Compose, Makefile, `.env.example`, auto OpenAPI docs |
| **CI/CD** | GitHub Actions: lint → typecheck → test → build → push Docker image |
| **Packaging** | `pyproject.toml` (uv), published wheel to TestPyPI |

---

## 🏗️ Final Project Structure

```
task-manager/
├── .github/
│   └── workflows/
│       └── ci.yml                    # lint → typecheck → test → docker build
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_create_users.py
│       ├── 002_create_tasks.py
│       ├── 003_create_tags.py
│       └── 004_create_comments.py
├── src/
│   └── task_manager/
│       ├── __init__.py               # exposes __version__
│       ├── main.py                   # FastAPI app + lifespan
│       ├── config.py                 # Pydantic Settings
│       ├── db.py                     # engine, session factory, health-check
│       ├── deps.py                   # DI: db session, current user, rate limiter
│       ├── logging_config.py         # structlog JSON config
│       ├── metrics.py                # Prometheus counters/histograms
│       ├── middleware/
│       │   ├── __init__.py
│       │   ├── request_id.py         # X-Request-ID header
│       │   ├── timing.py             # X-Response-Time header
│       │   └── security_headers.py   # HSTS, X-Frame-Options, etc.
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py               # DeclarativeBase + TimestampMixin
│       │   ├── user.py
│       │   ├── task.py
│       │   ├── tag.py
│       │   └── comment.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── user.py
│       │   ├── task.py
│       │   ├── tag.py
│       │   └── pagination.py         # generic Page[T]
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── auth.py               # /auth/register, /login, /refresh, /logout
│       │   ├── users.py              # /users/me, /users/{id}
│       │   ├── tasks.py              # full CRUD + /complete + tags
│       │   ├── tags.py
│       │   └── health.py             # /health, /metrics
│       ├── services/
│       │   ├── auth.py               # JWT + Argon2 password hashing
│       │   ├── tasks.py              # business logic
│       │   └── email.py              # async email (asyncio.Queue worker)
│       ├── repositories/
│       │   ├── base.py               # Generic[T] CRUD
│       │   ├── user.py
│       │   └── task.py
│       └── workers/
│           ├── email_worker.py       # asyncio background worker
│           └── cleanup_worker.py     # nightly soft-delete cleanup
├── tests/
│   ├── conftest.py                   # engine, session, client, factories
│   ├── factories.py                  # factory_boy model factories
│   ├── unit/
│   │   ├── test_auth_service.py
│   │   ├── test_task_service.py
│   │   └── test_schemas.py
│   └── integration/
│       ├── test_auth.py
│       ├── test_tasks.py
│       ├── test_tags.py
│       └── test_health.py
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── docker-compose.yml                # postgres + redis + api
├── docker-compose.test.yml           # isolated test postgres
├── pyproject.toml
├── uv.lock
├── Makefile
├── .env.example
├── .pre-commit-config.yaml
└── README.md
```

---

## Step 1 — Bootstrap & Config

### `pyproject.toml`

```toml
[project]
name = "task-manager"
version = "0.1.0"
description = "Production-grade async Task Management API"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.8",
    "pydantic-settings>=2.5",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "aiosqlite>=0.20",           # test DB
    "alembic>=1.13",
    "pyjwt[crypto]>=2.9",
    "argon2-cffi>=23.1",         # password hashing
    "redis>=5.0",                # rate limiting
    "structlog>=24.0",           # structured logging
    "prometheus-fastapi-instrumentator>=7.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "pytest-mock>=3.14",
    "httpx>=0.27",
    "factory-boy>=3.3",
    "mypy>=1.11",
    "ruff>=0.6",
    "pre-commit>=3.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/task_manager"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "UP", "B", "SIM", "S"]
ignore = ["S101"]   # allow assert in tests

[tool.mypy]
strict = true
python_version = "3.12"
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=90"

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError"]

[tool.hatch.version]
path = "src/task_manager/__init__.py"
```

### `.env.example`

```bash
# Copy to .env and fill in values

# App
APP_ENV=development          # development | staging | production
SECRET_KEY=CHANGE-THIS-USE-openssl-rand-hex-32
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/task_manager
TEST_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/task_manager_test

# Auth
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (rate limiting)
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=60

# Email (background worker)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=noreply@taskmanager.local

# CORS
CORS_ORIGINS=["http://localhost:3000","https://app.yourdomain.com"]
```

### `src/task_manager/config.py`

```python
from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "Task Manager API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/task_manager"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Auth
    secret_key: str = "CHANGE-ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 60

    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@taskmanager.local"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Step 2 — Logging & Metrics

### `src/task_manager/logging_config.py`

```python
"""Structured JSON logging via structlog."""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(debug: bool = False) -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if debug:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer]
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # Quiet noisy libraries
    for lib in ("uvicorn.access", "sqlalchemy.engine", "aiohttp"):
        logging.getLogger(lib).setLevel(logging.WARNING)
```

### `src/task_manager/metrics.py`

```python
"""Prometheus metrics definitions."""
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ACTIVE_USERS = Gauge("active_users_total", "Currently active users")

TASK_OPERATIONS = Counter(
    "task_operations_total",
    "Task CRUD operations",
    ["operation", "status"],
)

EMAIL_QUEUE_SIZE = Gauge("email_queue_size", "Pending emails in queue")
```

---

## Step 3 — Database & Models

### `src/task_manager/db.py`

```python
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,          # test connection before use
    pool_recycle=3600,           # recycle connections after 1 hour
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def check_db_health() -> bool:
    """Ping the database. Used by /health endpoint."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("db_health_check_failed", error=str(exc))
        return False


async def create_all_tables() -> None:
    """Create tables (dev/test only — use Alembic in production)."""
    from .models.base import Base
    from .models import user, task, tag, comment  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### `src/task_manager/models/base.py`

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### `src/task_manager/models/user.py`

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .task import Task


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="raise",          # prevent accidental N+1 — must use selectinload explicitly
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"
```

### `src/task_manager/models/task.py`

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .tag import Tag
    from .comment import Comment

task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    owner: Mapped[User] = relationship("User", back_populates="tasks", lazy="raise")
    tags: Mapped[list[Tag]] = relationship(
        "Tag", secondary=task_tags, back_populates="tasks", lazy="raise"
    )
    comments: Mapped[list[Comment]] = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan", lazy="raise"
    )

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r})"
```

---

## Step 4 — Auth Service (Argon2 + JWT)

### `src/task_manager/services/auth.py`

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Argon2id — winner of the Password Hashing Competition; much stronger than bcrypt
_ph = PasswordHasher(
    time_cost=2,         # iterations
    memory_cost=65536,   # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def _make_token(payload: dict, expire: timedelta) -> str:
    data = {**payload, "exp": datetime.now(timezone.utc) + expire}
    return jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: int) -> str:
    return _make_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: int) -> str:
    return _make_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str = "access") -> int:
    """Decode and validate a JWT. Returns user_id or raises ValueError."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc

    if payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}'")

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Token missing subject")
    return int(user_id)
```

---

## Step 5 — Dependencies

### `src/task_manager/deps.py`

```python
from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .db import AsyncSessionLocal
from .services.auth import decode_token

logger = structlog.get_logger(__name__)
_security = HTTPBearer(auto_error=False)


# ── Database ─────────────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Auth ──────────────────────────────────────────────────────────────────────
async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> int:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_token(credentials.credentials, expected_type="access")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


# ── Rate Limiter ──────────────────────────────────────────────────────────────
async def rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Sliding-window rate limit per IP using Redis."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"rl:{client_ip}"

    redis: aioredis.Redis = request.app.state.redis  # type: ignore[attr-defined]
    async with redis.pipeline(transaction=True) as pipe:
        try:
            await pipe.incr(key)
            await pipe.expire(key, 60)
            results = await pipe.execute()
            count: int = results[0]
        except Exception:
            logger.warning("rate_limiter_redis_error", ip=client_ip)
            return  # fail open if Redis is down

    if count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )


# ── Type aliases for injection ────────────────────────────────────────────────
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
AppSettings = Annotated[Settings, Depends(get_settings)]
RateLimited = Annotated[None, Depends(rate_limit)]
```

---

## Step 6 — Schemas

### `src/task_manager/schemas/pagination.py`

```python
from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)

    @computed_field  # type: ignore[misc]
    @property
    def pages(self) -> int:
        return max(1, math.ceil(self.total / self.size))

    @computed_field  # type: ignore[misc]
    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @computed_field  # type: ignore[misc]
    @property
    def has_prev(self) -> bool:
        return self.page > 1
```

### `src/task_manager/schemas/task.py`

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TagOut(BaseModel):
    id: int
    name: str
    color: str | None = None
    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, examples=["Buy groceries"])
    description: str | None = Field(None, max_length=5000)
    priority: int = Field(default=1, ge=1, le=5)


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    priority: int | None = Field(None, ge=1, le=5)


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    priority: int
    is_complete: bool
    owner_id: int
    tags: list[TagOut] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
```

---

## Step 7 — Repositories

### `src/task_manager/repositories/base.py`

```python
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get(self, id: int) -> ModelT | None:
        return await self._session.get(self._model, id)

    async def get_or_404(self, id: int) -> ModelT:
        from fastapi import HTTPException, status
        obj = await self.get(id)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self._model.__name__} {id} not found",
            )
        return obj

    async def create(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)

    async def _paginate(
        self,
        stmt: Select[Any],
        page: int,
        size: int,
    ) -> tuple[list[ModelT], int]:
        # Total count (without pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        # Paginated results
        result = await self._session.execute(stmt.offset((page - 1) * size).limit(size))
        items = list(result.scalars().unique().all())

        return items, total
```

### `src/task_manager/repositories/task.py`

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from ..models.tag import Tag
from ..models.task import Task
from .base import BaseRepository


class TaskRepository(BaseRepository[Task]):

    async def get_with_relations(self, task_id: int) -> Task | None:
        result = await self._session.execute(
            select(Task)
            .where(Task.id == task_id, Task.is_deleted.is_(False))
            .options(
                selectinload(Task.tags),
                selectinload(Task.comments),
                joinedload(Task.owner),
            )
        )
        return result.scalars().first()

    async def list_for_owner(
        self,
        owner_id: int,
        *,
        page: int = 1,
        size: int = 20,
        priority: int | None = None,
        is_complete: bool | None = None,
        tag_name: str | None = None,
    ) -> tuple[list[Task], int]:
        stmt = (
            select(Task)
            .where(Task.owner_id == owner_id, Task.is_deleted.is_(False))
            .options(selectinload(Task.tags))
            .order_by(Task.created_at.desc())
        )
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if is_complete is not None:
            stmt = stmt.where(Task.is_complete.is_(is_complete))
        if tag_name is not None:
            stmt = stmt.join(Task.tags).where(Tag.name == tag_name)

        return await self._paginate(stmt, page, size)
```

---

## Step 8 — Routers

### `src/task_manager/routers/auth.py`

```python
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from ..db import AsyncSessionLocal
from ..deps import DbSession, RateLimited
from ..models.user import User
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from ..services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession, _: RateLimited) -> TokenResponse:
    # Check duplicate email
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("user_registered", user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession, _: RateLimited) -> TokenResponse:
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        # Same error for both: prevent user enumeration
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    logger.info("user_logged_in", user_id=user.id)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: dict, _: RateLimited) -> TokenResponse:
    token = payload.get("refresh_token", "")
    try:
        user_id = decode_token(token, expected_type="refresh")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
```

### `src/task_manager/routers/tasks.py`

```python
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from ..deps import CurrentUserId, DbSession, RateLimited
from ..metrics import TASK_OPERATIONS
from ..models.task import Task
from ..repositories.task import TaskRepository
from ..schemas.pagination import Page
from ..schemas.task import TaskCreate, TaskOut, TaskUpdate
from ..services.email import enqueue_task_created_email

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


def _assert_owner(task: Task, user_id: int) -> None:
    if task.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")


@router.get("/", response_model=Page[TaskOut])
async def list_tasks(
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    priority: int | None = Query(None, ge=1, le=5),
    is_complete: bool | None = Query(None),
    tag: str | None = Query(None, max_length=50),
) -> Page[TaskOut]:
    repo = TaskRepository(Task, db)
    tasks, total = await repo.list_for_owner(
        user_id, page=page, size=size, priority=priority, is_complete=is_complete, tag_name=tag
    )
    return Page(items=tasks, total=total, page=page, size=size)


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: DbSession,
    user_id: CurrentUserId,
    _: RateLimited,
) -> TaskOut:
    repo = TaskRepository(Task, db)
    task = Task(**payload.model_dump(), owner_id=user_id)
    task = await repo.create(task)
    TASK_OPERATIONS.labels(operation="create", status="success").inc()
    logger.info("task_created", task_id=task.id, user_id=user_id)
    await enqueue_task_created_email(user_id, task.title)
    return TaskOut.model_validate(task)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: DbSession, user_id: CurrentUserId) -> TaskOut:
    repo = TaskRepository(Task, db)
    task = await repo.get_with_relations(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _assert_owner(task, user_id)
    return TaskOut.model_validate(task)


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskUpdate, db: DbSession, user_id: CurrentUserId
) -> TaskOut:
    repo = TaskRepository(Task, db)
    task = await repo.get_or_404(task_id)
    _assert_owner(task, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    TASK_OPERATIONS.labels(operation="update", status="success").inc()
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: DbSession, user_id: CurrentUserId) -> None:
    repo = TaskRepository(Task, db)
    task = await repo.get_or_404(task_id)
    _assert_owner(task, user_id)
    task.is_deleted = True  # soft delete
    TASK_OPERATIONS.labels(operation="delete", status="success").inc()
    logger.info("task_soft_deleted", task_id=task_id, user_id=user_id)


@router.patch("/{task_id}/complete", response_model=TaskOut)
async def complete_task(task_id: int, db: DbSession, user_id: CurrentUserId) -> TaskOut:
    repo = TaskRepository(Task, db)
    task = await repo.get_or_404(task_id)
    _assert_owner(task, user_id)
    task.is_complete = True
    await db.flush()
    await db.refresh(task)
    return TaskOut.model_validate(task)
```

### `src/task_manager/routers/health.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..config import get_settings
from ..db import check_db_health

router = APIRouter(tags=["ops"])
settings = get_settings()


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    db_ok = await check_db_health()
    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": settings.app_version,
        "db": "ok" if db_ok else "unreachable",
    }
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(content=str(payload), status_code=code, media_type="application/json")


@router.get("/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    """Prometheus scrape endpoint."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

## Step 9 — Middleware

### `src/task_manager/middleware/request_id.py`

```python
from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### `src/task_manager/middleware/security_headers.py`

```python
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        })
        return response
```

---

## Step 10 — Main App

### `src/task_manager/main.py`

```python
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import create_all_tables
from .logging_config import configure_logging
from .middleware.request_id import RequestIDMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .routers import auth, health, tags, tasks, users
from .workers.cleanup_worker import cleanup_scheduler
from .workers.email_worker import email_worker

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ── Startup ────────────────────────────────────────────────────────
    configure_logging(debug=settings.debug)
    logger.info("startup", env=settings.app_env, version=settings.app_version)

    # DB (dev/test only; use Alembic in production)
    if not settings.is_production:
        await create_all_tables()

    # Redis
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    # Background workers
    workers = [
        asyncio.create_task(email_worker(), name="email-worker"),
        asyncio.create_task(cleanup_scheduler(), name="cleanup-worker"),
    ]
    logger.info("workers_started", count=len(workers))

    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    await app.state.redis.aclose()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # Middleware (order matters — outermost runs first on request, last on response)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(tasks.router)
    app.include_router(tags.router)

    return app


app = create_app()
```

---

## Step 11 — Full Test Suite

### `tests/conftest.py`

```python
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.task_manager.db import AsyncSessionLocal
from src.task_manager.deps import get_current_user_id, get_db
from src.task_manager.main import app
from src.task_manager.models.base import Base
from src.task_manager.models import user, task, tag, comment  # noqa: F401
from src.task_manager.services.auth import create_access_token, hash_password
from src.task_manager.models.user import User
from src.task_manager.models.task import Task

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine) -> AsyncSession:
    """Each test gets a rolled-back transaction."""
    async with test_engine.begin() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    u = User(
        email="test@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Test User",
        is_active=True,
    )
    db.add(u)
    await db.flush()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_task(db: AsyncSession, test_user: User) -> Task:
    t = Task(title="Sample Task", priority=2, owner_id=test_user.id)
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


@pytest_asyncio.fixture
async def client(db: AsyncSession, test_user: User) -> AsyncClient:
    async def _db():
        yield db

    async def _auth():
        return test_user.id

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user_id] = _auth
    # Stub Redis for rate limiter
    from unittest.mock import AsyncMock, MagicMock
    app.state.redis = MagicMock()
    app.state.redis.pipeline.return_value.__aenter__ = AsyncMock(
        return_value=MagicMock(
            incr=AsyncMock(), expire=AsyncMock(), execute=AsyncMock(return_value=[1, True])
        )
    )
    app.state.redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

### `tests/unit/test_auth_service.py`

```python
import pytest
from src.task_manager.services.auth import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("MyP@ssw0rd!")
    assert hashed != "MyP@ssw0rd!"
    assert verify_password("MyP@ssw0rd!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_round_trip():
    token = create_access_token(42)
    assert decode_token(token, "access") == 42


def test_refresh_token_round_trip():
    token = create_refresh_token(99)
    assert decode_token(token, "refresh") == 99


def test_wrong_token_type_raises():
    access = create_access_token(1)
    with pytest.raises(ValueError, match="Expected token type 'refresh'"):
        decode_token(access, "refresh")


def test_tampered_token_raises():
    with pytest.raises(ValueError, match="Invalid token"):
        decode_token("not.a.real.token")
```

### `tests/integration/test_tasks.py`

```python
import pytest
from httpx import AsyncClient
from src.task_manager.models.task import Task


class TestCreateTask:
    async def test_success(self, client: AsyncClient):
        r = await client.post("/tasks/", json={"title": "Buy milk", "priority": 2})
        assert r.status_code == 201
        d = r.json()
        assert d["title"] == "Buy milk"
        assert d["is_complete"] is False

    async def test_title_too_long(self, client: AsyncClient):
        r = await client.post("/tasks/", json={"title": "x" * 201})
        assert r.status_code == 422

    @pytest.mark.parametrize("priority", [0, 6, -1])
    async def test_invalid_priority(self, client: AsyncClient, priority: int):
        r = await client.post("/tasks/", json={"title": "T", "priority": priority})
        assert r.status_code == 422

    async def test_unauthenticated(self, client: AsyncClient):
        client.headers.clear()
        r = await client.post("/tasks/", json={"title": "T"})
        assert r.status_code == 401


class TestGetTask:
    async def test_success(self, client: AsyncClient, sample_task: Task):
        r = await client.get(f"/tasks/{sample_task.id}")
        assert r.status_code == 200
        assert r.json()["id"] == sample_task.id

    async def test_not_found(self, client: AsyncClient):
        r = await client.get("/tasks/999999")
        assert r.status_code == 404


class TestUpdateTask:
    async def test_partial_update(self, client: AsyncClient, sample_task: Task):
        r = await client.put(f"/tasks/{sample_task.id}", json={"priority": 5})
        assert r.status_code == 200
        assert r.json()["priority"] == 5

    async def test_complete_task(self, client: AsyncClient, sample_task: Task):
        r = await client.patch(f"/tasks/{sample_task.id}/complete")
        assert r.status_code == 200
        assert r.json()["is_complete"] is True


class TestDeleteTask:
    async def test_soft_delete(self, client: AsyncClient, sample_task: Task):
        r = await client.delete(f"/tasks/{sample_task.id}")
        assert r.status_code == 204
        # Verify soft-deleted: GET returns 404
        r2 = await client.get(f"/tasks/{sample_task.id}")
        assert r2.status_code == 404


class TestListTasks:
    async def test_pagination(self, client: AsyncClient):
        r = await client.get("/tasks/?page=1&size=5")
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d and "pages" in d

    async def test_filter_by_complete(self, client: AsyncClient):
        r = await client.get("/tasks/?is_complete=false")
        assert r.status_code == 200
```

### `tests/integration/test_health.py`

```python
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code in (200, 503)
    assert "status" in r.json()
```

---

## Step 12 — Docker & Docker Compose

### `docker/Dockerfile`

```dockerfile
# ── Build stage ───────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/

# ── Runtime stage ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY alembic/ alembic/
COPY alembic.ini .
COPY docker/entrypoint.sh .

RUN chmod +x entrypoint.sh && chown -R appuser:appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

ENTRYPOINT ["./entrypoint.sh"]
```

### `docker/entrypoint.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn src.task_manager.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --loop uvloop \
    --http httptools \
    --no-access-log
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: task_manager
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports: ["8000:8000"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@postgres:5432/task_manager
      REDIS_URL: redis://redis:6379/0
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## Step 13 — CI/CD (GitHub Actions)

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"
  IMAGE_NAME: ghcr.io/${{ github.repository }}

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra dev
      - name: Lint (ruff)
        run: uv run ruff check src/ tests/
      - name: Format check (ruff)
        run: uv run ruff format --check src/ tests/
      - name: Type check (mypy --strict)
        run: uv run mypy src/ --strict

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_DB: task_manager_test
        ports: ["5433:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 3s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra dev
      - name: Run tests with coverage
        env:
          APP_ENV: development
          SECRET_KEY: test-secret-key-for-ci-only
          DATABASE_URL: postgresql+asyncpg://postgres:password@localhost:5433/task_manager_test
          REDIS_URL: redis://localhost:6379/0
        run: uv run pytest --cov-fail-under=90
      - name: Upload coverage report
        uses: codecov/codecov-action@v4

  build-and-push:
    needs: [lint-and-typecheck, test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile
          push: true
          tags: |
            ${{ env.IMAGE_NAME }}:latest
            ${{ env.IMAGE_NAME }}:${{ github.sha }}
```

---

## Step 14 — Makefile

```makefile
.PHONY: help install dev-setup run test lint typecheck migrate format clean docker-up docker-down

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:         ## Install all dependencies
	uv sync --extra dev

dev-setup:       ## Full local dev setup
	cp -n .env.example .env
	uv sync --extra dev
	uv run pre-commit install
	docker-compose up -d postgres redis
	sleep 3
	uv run alembic upgrade head

run:             ## Start API server (hot-reload)
	uv run uvicorn src.task_manager.main:app --reload --port 8000

test:            ## Run full test suite
	uv run pytest -v

test-fast:       ## Run tests (no coverage, fail-fast)
	uv run pytest -x -q --no-cov

lint:            ## Run ruff linter
	uv run ruff check src/ tests/

format:          ## Auto-format with ruff
	uv run ruff format src/ tests/

typecheck:       ## Run mypy --strict
	uv run mypy src/ --strict

migrate:         ## Run pending Alembic migrations
	uv run alembic upgrade head

migrate-new:     ## Create a new migration (m="description")
	uv run alembic revision --autogenerate -m "$(m)"

docker-up:       ## Start full stack with Docker Compose
	docker-compose up -d --build

docker-down:     ## Stop all containers
	docker-compose down -v

clean:           ## Remove caches and build artifacts
	find . -type d -name __pycache__ | xargs rm -rf
	find . -name "*.pyc" -delete
	rm -rf .mypy_cache .ruff_cache htmlcov .coverage dist
```

---

## ✅ Production Checklist

### Security
- [ ] Argon2id password hashing (not bcrypt)
- [ ] JWT: short-lived access (15 min) + long-lived refresh (7 days)
- [ ] Rate limiter on all auth endpoints (Redis sliding window)
- [ ] Security headers middleware (HSTS, X-Frame-Options, CSP)
- [ ] CORS restricted to explicit origins
- [ ] User enumeration prevented in login (same error for bad user/bad password)
- [ ] Docs disabled in production (`docs_url=None`)

### Reliability
- [ ] `pool_pre_ping=True` on DB engine
- [ ] Graceful shutdown: cancel background tasks, close Redis
- [ ] Alembic migrations in Docker entrypoint
- [ ] `/health` pings DB; returns 503 if unhealthy

### Observability
- [ ] Structured JSON logging with structlog (request_id on every log line)
- [ ] Prometheus metrics at `/metrics` (request count, latency, task ops)
- [ ] `X-Request-ID` header on every response

### Code Quality
- [ ] `mypy --strict` passes (0 errors)
- [ ] `ruff` passes (lint + format)
- [ ] pre-commit hooks block bad commits
- [ ] 90 %+ test coverage

### Developer Experience
- [ ] `make dev-setup` boots everything in one command
- [ ] `.env.example` documents every variable
- [ ] Auto-generated Swagger UI at `/docs`
- [ ] GitHub Actions: lint → typecheck → test → Docker push on main
