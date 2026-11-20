# Pillar 9 — Capstone Project: Task Manager API

> **Duration:** 2 weeks | Combines ALL 8 pillars

---

## 🎯 Project Goal

Build a **production-grade Task Management REST API** that demonstrates mastery of every
skill in this curriculum. This is the project you show in interviews.

---

## 🏗️ Architecture Overview

```
task-manager/
├── pyproject.toml                 # Pillar 4: packaging with hatch/uv
├── uv.lock                        # dependency lockfile
├── README.md
├── .env.example
├── alembic/                       # Pillar 6: DB migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_create_users.py
│       ├── 002_create_tasks.py
│       ├── 003_create_tags.py
│       └── 004_create_comments.py
├── src/
│   └── task_manager/
│       ├── __init__.py            # exposes __version__
│       ├── main.py                # FastAPI app + lifespan
│       ├── config.py              # Pydantic Settings
│       ├── db.py                  # engine, session factory
│       ├── deps.py                # DI dependencies
│       ├── models/                # Pillar 6: SQLAlchemy models
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── user.py
│       │   ├── task.py
│       │   ├── tag.py
│       │   └── comment.py
│       ├── schemas/               # Pydantic v2 request/response schemas
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── task.py
│       │   └── auth.py
│       ├── routers/               # Pillar 5: FastAPI routers
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── users.py
│       │   ├── tasks.py
│       │   └── tags.py
│       ├── services/              # Business logic layer
│       │   ├── auth.py
│       │   ├── tasks.py
│       │   └── notifications.py
│       ├── repositories/          # Pillar 6: Repository pattern
│       │   ├── base.py
│       │   ├── user.py
│       │   └── task.py
│       └── workers/               # Pillar 2: asyncio background jobs
│           ├── email_worker.py
│           └── cleanup_worker.py
└── tests/
    ├── conftest.py                # Pillar 7: shared fixtures
    ├── unit/
    │   ├── test_services.py
    │   └── test_schemas.py
    └── integration/
        ├── test_auth.py
        ├── test_tasks.py
        └── test_tags.py
```

---

## ✅ Feature Checklist

### Authentication & Users
- [ ] `POST /auth/register` — create a new account
- [ ] `POST /auth/login` — returns JWT access token + refresh token
- [ ] `POST /auth/refresh` — exchange refresh token for new access token
- [ ] `GET /auth/me` — get current user profile
- [ ] JWT stored in memory (access, 15 min) + httpOnly cookie (refresh, 7 days)

### Tasks
- [ ] `GET /tasks` — list tasks (pagination, filter by status/priority/tag)
- [ ] `POST /tasks` — create task
- [ ] `GET /tasks/{id}` — get task with tags and comments
- [ ] `PUT /tasks/{id}` — update task
- [ ] `DELETE /tasks/{id}` — delete task (soft delete)
- [ ] `PATCH /tasks/{id}/complete` — mark as complete
- [ ] Task ownership: users can only see/edit their own tasks
- [ ] `POST /tasks/{id}/tags/{tag_id}` — attach tag to task
- [ ] `DELETE /tasks/{id}/tags/{tag_id}` — detach tag from task

### Tags
- [ ] `GET /tags` — list all tags
- [ ] `POST /tags` — create tag
- [ ] `DELETE /tags/{id}` — delete tag

### Comments
- [ ] `GET /tasks/{id}/comments` — list comments for a task
- [ ] `POST /tasks/{id}/comments` — add a comment

### Background Jobs (asyncio)
- [ ] Send email notification on task creation (non-blocking)
- [ ] Nightly cleanup: delete tasks completed > 30 days ago
- [ ] Log all API activity to audit log file

---

## Step-by-Step Build Guide

---

### Step 1 — Project Setup (Day 1)

```bash
mkdir task-manager && cd task-manager
uv init .
uv add fastapi uvicorn[standard] pydantic pydantic-settings sqlalchemy[asyncio] asyncpg aiosqlite alembic pyjwt passlib bcrypt python-multipart
uv add --dev pytest pytest-asyncio pytest-cov pytest-mock httpx factory-boy mypy ruff
```

```toml
# pyproject.toml
[project]
name = "task-manager"
version = "0.1.0"
description = "Production-grade Task Management API"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "aiosqlite>=0.20",
    "alembic>=1.13",
    "pyjwt>=2.8",
    "passlib[bcrypt]>=1.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "pytest-mock>=3.14",
    "httpx>=0.27",
    "factory-boy>=3.3",
    "mypy>=1.10",
    "ruff>=0.4",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=src --cov-report=html --cov-report=term-missing"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "UP", "B", "SIM"]
```

---

### Step 2 — Configuration (Day 1)

```python
# src/task_manager/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # App
    app_name: str = "Task Manager API"
    debug: bool = False
    version: str = "0.1.0"

    # Database
    database_url: str = "sqlite+aiosqlite:///./task_manager.db"

    # Auth
    secret_key: str = "CHANGE-THIS-IN-PRODUCTION-USE-256-BIT-KEY"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Email (for background worker)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@taskmanager.local"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

### Step 3 — Database Setup (Day 1–2)

```python
# src/task_manager/db.py
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from .config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def create_tables() -> None:
    from .models.base import Base
    from .models import user, task, tag, comment  # noqa: F401 — register models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

### Step 4 — Models (Day 2–3) — Pillar 6

```python
# src/task_manager/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

```python
# src/task_manager/models/user.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean
from .base import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .task import Task
    from .tag import Tag

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"
```

```python
# src/task_manager/models/task.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, Table, Column
from .base import Base, TimestampMixin
from typing import TYPE_CHECKING

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
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner: Mapped["User"] = relationship("User", back_populates="tasks")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=task_tags, back_populates="tasks")
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r})"
```

---

### Step 5 — Schemas (Day 3) — Pillar 8 (typing)

```python
# src/task_manager/schemas/task.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"

class TagSchema(BaseModel):
    id: int
    name: str
    color: str | None
    model_config = {"from_attributes": True}

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    priority: int = Field(default=1, ge=1, le=5)

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    priority: int
    is_complete: bool
    owner_id: int
    tags: list[TagSchema] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    size: int
    pages: int
```

---

### Step 6 — Repositories (Day 4) — Pillar 6 + 8

```python
# src/task_manager/repositories/base.py
from typing import Generic, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base_model import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, id: int) -> T | None:
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(self.model.id)))
        return result.scalar_one()

    async def create(self, instance: T) -> T:
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: T) -> None:
        await self.session.delete(instance)
```

```python
# src/task_manager/repositories/task.py
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from .base import BaseRepository
from ..models.task import Task

class TaskRepository(BaseRepository[Task]):
    async def get_with_relations(self, task_id: int) -> Task | None:
        result = await self.session.execute(
            select(Task)
            .where(Task.id == task_id, Task.is_deleted == False)
            .options(
                selectinload(Task.tags),
                selectinload(Task.comments),
                joinedload(Task.owner),
            )
        )
        return result.scalars().first()

    async def get_by_owner(
        self,
        owner_id: int,
        skip: int = 0,
        limit: int = 20,
        priority: int | None = None,
        is_complete: bool | None = None,
    ) -> tuple[list[Task], int]:
        query = (
            select(Task)
            .where(Task.owner_id == owner_id, Task.is_deleted == False)
            .options(selectinload(Task.tags))
            .order_by(Task.created_at.desc())
        )
        if priority is not None:
            query = query.where(Task.priority == priority)
        if is_complete is not None:
            query = query.where(Task.is_complete == is_complete)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        result = await self.session.execute(query.offset(skip).limit(limit))
        tasks = list(result.scalars().all())

        return tasks, total
```

---

### Step 7 — Auth Service (Day 4–5) — Pillar 5

```python
# src/task_manager/services/auth.py
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from ..config import get_settings
from ..models.user import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
```

---

### Step 8 — Dependencies (Day 5) — Pillar 5

```python
# src/task_manager/deps.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .db import AsyncSessionLocal
from .config import Settings, get_settings
from .services.auth import decode_token

security = HTTPBearer()

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return int(payload["sub"])
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

# Convenience type aliases for Annotated injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
AppSettings = Annotated[Settings, Depends(get_settings)]
```

---

### Step 9 — Routers (Day 5–6) — Pillar 5

```python
# src/task_manager/routers/tasks.py
from fastapi import APIRouter, HTTPException, Query
from ..deps import DbSession, CurrentUserId
from ..repositories.task import TaskRepository
from ..models.task import Task
from ..schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    db: DbSession,
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    priority: int | None = Query(None, ge=1, le=5),
    is_complete: bool | None = Query(None),
) -> TaskListResponse:
    repo = TaskRepository(Task, db)
    skip = (page - 1) * size
    tasks, total = await repo.get_by_owner(user_id, skip, size, priority, is_complete)
    pages = (total + size - 1) // size
    return TaskListResponse(items=tasks, total=total, page=page, size=size, pages=pages)

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    db: DbSession,
    user_id: CurrentUserId,
) -> TaskResponse:
    repo = TaskRepository(Task, db)
    task = Task(**task_data.model_dump(), owner_id=user_id)
    task = await repo.create(task)
    return TaskResponse.model_validate(task)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: DbSession, user_id: CurrentUserId) -> TaskResponse:
    repo = TaskRepository(Task, db)
    task = await repo.get_with_relations(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return TaskResponse.model_validate(task)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int, update: TaskUpdate, db: DbSession, user_id: CurrentUserId
) -> TaskResponse:
    repo = TaskRepository(Task, db)
    task = await repo.get(task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    return TaskResponse.model_validate(task)

@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: DbSession, user_id: CurrentUserId) -> None:
    repo = TaskRepository(Task, db)
    task = await repo.get(task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    task.is_deleted = True   # soft delete

@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int, db: DbSession, user_id: CurrentUserId) -> TaskResponse:
    repo = TaskRepository(Task, db)
    task = await repo.get(task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    task.is_complete = True
    await db.flush()
    await db.refresh(task)
    return TaskResponse.model_validate(task)
```

---

### Step 10 — Background Workers (Day 6–7) — Pillar 2

```python
# src/task_manager/workers/email_worker.py
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory queue for email jobs
email_queue: asyncio.Queue[dict] = asyncio.Queue()

async def enqueue_task_created_email(user_email: str, task_title: str) -> None:
    """Add an email job to the queue (non-blocking)."""
    await email_queue.put({
        "type": "task_created",
        "to": user_email,
        "subject": f"Task created: {task_title}",
        "body": f"Your task '{task_title}' has been created successfully.",
        "timestamp": datetime.utcnow().isoformat(),
    })

async def email_worker() -> None:
    """Background coroutine: processes email queue."""
    logger.info("Email worker started")
    while True:
        try:
            job = await asyncio.wait_for(email_queue.get(), timeout=1.0)
            logger.info(f"Sending email to {job['to']}: {job['subject']}")
            await _send_email(job)
            email_queue.task_done()
        except asyncio.TimeoutError:
            continue   # no jobs right now, loop back
        except Exception as e:
            logger.error(f"Email worker error: {e}")

async def _send_email(job: dict) -> None:
    """Simulate async email sending."""
    await asyncio.sleep(0.1)
    logger.debug(f"[EMAIL] To: {job['to']} | Subject: {job['subject']}")
```

```python
# src/task_manager/workers/cleanup_worker.py
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import delete
from ..db import AsyncSessionLocal
from ..models.task import Task

logger = logging.getLogger(__name__)

async def cleanup_old_tasks() -> int:
    """Delete tasks completed more than 30 days ago."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Task).where(
                Task.is_complete == True,
                Task.updated_at < cutoff,
                Task.is_deleted == True,
            )
        )
        await session.commit()
        count = result.rowcount
        logger.info(f"Cleaned up {count} old tasks")
        return count

async def cleanup_scheduler() -> None:
    """Run cleanup once per day."""
    while True:
        try:
            await cleanup_old_tasks()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        await asyncio.sleep(60 * 60 * 24)   # 24 hours
```

---

### Step 11 — Main App with Lifespan (Day 7) — Pillar 5

```python
# src/task_manager/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import create_tables
from .routers import auth, users, tasks, tags
from .workers.email_worker import email_worker
from .workers.cleanup_worker import cleanup_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Task Manager API...")

    # Create DB tables (in production, use Alembic instead)
    await create_tables()

    # Start background workers
    email_task = asyncio.create_task(email_worker())
    cleanup_task = asyncio.create_task(cleanup_scheduler())

    logger.info("Background workers started")
    yield

    # Shutdown: cancel background tasks
    email_task.cancel()
    cleanup_task.cancel()
    try:
        await asyncio.gather(email_task, cleanup_task, return_exceptions=True)
    except Exception:
        pass
    logger.info("Task Manager API shut down")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(tags.router)

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": settings.version}
```

---

### Step 12 — Tests (Day 8–10) — Pillar 7

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.task_manager.main import app
from src.task_manager.deps import get_db, get_current_user_id
from src.task_manager.models.base import Base
from src.task_manager.models import user, task, tag, comment  # noqa
from src.task_manager.services.auth import create_access_token, hash_password
from src.task_manager.models.user import User
from src.task_manager.models.task import Task

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db(test_engine) -> AsyncSession:
    """Rollback after each test."""
    async with test_engine.begin() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()

@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        full_name="Test User",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def client(db: AsyncSession, test_user: User) -> AsyncClient:
    async def override_db():
        yield db

    async def override_auth():
        return test_user.id

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_id] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def sample_task(db: AsyncSession, test_user: User) -> Task:
    task = Task(title="Sample Task", priority=2, owner_id=test_user.id)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task
```

```python
# tests/integration/test_tasks.py
import pytest
from httpx import AsyncClient
from src.task_manager.models.task import Task

class TestCreateTask:
    async def test_success(self, client: AsyncClient):
        r = await client.post("/tasks/", json={"title": "New Task", "priority": 3})
        assert r.status_code == 201
        assert r.json()["title"] == "New Task"
        assert r.json()["priority"] == 3
        assert r.json()["is_complete"] is False

    async def test_missing_title(self, client: AsyncClient):
        r = await client.post("/tasks/", json={"priority": 2})
        assert r.status_code == 422

    @pytest.mark.parametrize("priority", [0, 6, -1])
    async def test_invalid_priority(self, client: AsyncClient, priority: int):
        r = await client.post("/tasks/", json={"title": "T", "priority": priority})
        assert r.status_code == 422

class TestGetTask:
    async def test_get_own_task(self, client: AsyncClient, sample_task: Task):
        r = await client.get(f"/tasks/{sample_task.id}")
        assert r.status_code == 200
        assert r.json()["id"] == sample_task.id

    async def test_not_found(self, client: AsyncClient):
        r = await client.get("/tasks/99999")
        assert r.status_code == 404

class TestCompleteTask:
    async def test_complete(self, client: AsyncClient, sample_task: Task):
        r = await client.patch(f"/tasks/{sample_task.id}/complete")
        assert r.status_code == 200
        assert r.json()["is_complete"] is True

class TestDeleteTask:
    async def test_soft_delete(self, client: AsyncClient, sample_task: Task):
        r = await client.delete(f"/tasks/{sample_task.id}")
        assert r.status_code == 204

        # Verify it's gone
        r = await client.get(f"/tasks/{sample_task.id}")
        assert r.status_code == 404
```

---

### Step 13 — Alembic Migrations (Day 10–11) — Pillar 6

```bash
alembic init alembic
# Edit alembic/env.py to use your models and async engine

alembic revision --autogenerate -m "create_users_table"
alembic revision --autogenerate -m "create_tasks_table"
alembic revision --autogenerate -m "create_tags_table"
alembic revision --autogenerate -m "create_comments_table"
alembic revision --autogenerate -m "add_task_tags_association"

# Review each migration file, then:
alembic upgrade head
```

---

### Step 14 — mypy and CI (Day 11–12) — Pillar 8 + 4

```bash
# Run mypy
mypy src/ --strict

# Fix all errors:
# 1. Add missing annotations
# 2. Add `# type: ignore[import]` for untyped libraries
# 3. Use `cast()` where needed

# Run full check
ruff check src/ tests/
mypy src/
pytest --cov=src --cov-fail-under=85
```

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra dev
      - run: uv run ruff check src/ tests/
      - run: uv run mypy src/ --strict
      - run: uv run pytest --cov=src --cov-fail-under=85
```

---

## 🏁 Done Checklist

### Code Quality
- [ ] `mypy --strict` passes with 0 errors
- [ ] `ruff check` passes
- [ ] All tests pass: `pytest`
- [ ] Coverage ≥ 85%: `pytest --cov-fail-under=85`

### Features
- [ ] Auth: register, login, refresh, /me
- [ ] Full CRUD for tasks with ownership enforcement
- [ ] Soft delete for tasks
- [ ] Tag management + task-tag M2M
- [ ] Comments on tasks
- [ ] Pagination on list endpoints
- [ ] Background email worker using `asyncio.Queue`
- [ ] Nightly cleanup worker with `asyncio.sleep`

### Production Readiness
- [ ] Request ID middleware
- [ ] Structured logging
- [ ] Health check endpoint
- [ ] `.env.example` with all config keys
- [ ] Alembic migrations for all tables
- [ ] Docker-ready (optional bonus)

### Packaging (Pillar 4)
- [ ] `pyproject.toml` with correct metadata
- [ ] Published to TestPyPI as a wheel
- [ ] `uv.lock` committed

---

## 📊 Skills Demonstrated

| Skill | Where Used |
|-------|-----------|
| Python Internals | Descriptors in `BaseRepository`, `__repr__`, `__slots__` in models |
| asyncio | Email worker, cleanup worker, `AsyncSession`, lifespan |
| threading | `ThreadPoolExecutor` via `run_in_executor` for blocking tasks |
| Performance Profiling | Profile a slow list endpoint, fix with eager loading |
| Packaging | `pyproject.toml`, uv, TestPyPI |
| FastAPI | Full API with DI, routers, middleware, lifespan, background tasks |
| SQLAlchemy 2.0 | Models, relationships, AsyncSession, eager loading, N+1 fix |
| Alembic | Full migration history, data migration example |
| pytest | Fixtures, parametrize, mocking, 85%+ coverage |
| mypy | Full strict mode on entire codebase |

---

## 🎓 Congratulations!

If you have completed all 8 pillars and built this capstone project, you have
demonstrated the Python mastery expected of a senior/staff Python engineer.

**Next steps:**
1. Write a blog post or README explaining your design decisions
2. Add a Dockerfile and `docker-compose.yml`
3. Add OpenTelemetry tracing
4. Add a rate limiter middleware
5. Submit to real PyPI and share the link in your portfolio
