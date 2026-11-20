# Pillar 6 — SQLAlchemy & Alembic

> **Duration:** 2 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Write ORM models in SQLAlchemy 2.0 style with full type safety
- Understand all relationship types and loading strategies
- Use `AsyncSession` with FastAPI
- Write and run Alembic migrations (including data migrations)
- Identify and fix the N+1 query problem
- Understand connection pool configuration

---

## 📚 Resources

| Resource | Type | Priority |
|----------|------|----------|
| [SQLAlchemy 2.0 Docs — ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) | 📄 Docs | Must |
| [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) | 📄 Docs | Must |
| *Architecture Patterns with Python* (cosmicpython.com) | 📖 Free Book | Must |
| [SQLAlchemy 2.0 migration guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html) | 📄 Docs | If you know 1.x |

---

## Section 1 — SQLAlchemy 2.0 Core Concepts

### The Two Layers

```
SQLAlchemy Core   — Low-level SQL expression language (table(), select(), insert())
SQLAlchemy ORM    — High-level: maps Python classes to tables
                    Built ON TOP of Core; you can mix both
```

### Engine and Connection

```python
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

# Sync engine (for scripts, Alembic)
engine = create_engine(
    "postgresql://user:pass@localhost/dbname",
    pool_size=10,          # number of persistent connections
    max_overflow=20,       # extra connections above pool_size
    pool_pre_ping=True,    # test connection health before use
    echo=False,            # True = log all SQL (dev only)
)

# Async engine (for FastAPI + asyncio)
async_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/dbname",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Using Core directly
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.fetchone())
```

---

## Section 2 — ORM Models (SQLAlchemy 2.0 Style)

### Declarative Base

```python
from sqlalchemy.orm import DeclarativeBase, MappedColumn, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin to add created_at and updated_at to any model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="user_tags", back_populates="users")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"
```

---

## Section 3 — Relationships in Depth

### One-to-Many

```python
class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)

    # Foreign key
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="tasks")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="task_tags", back_populates="tasks")
```

### Many-to-Many (Association Table)

```python
from sqlalchemy import Table, Column

# Association table (no class needed for simple M2M)
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

user_tags = Table(
    "user_tags",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # hex color

    tasks: Mapped[list["Task"]] = relationship("Task", secondary=task_tags, back_populates="tags")
    users: Mapped[list["User"]] = relationship("User", secondary=user_tags, back_populates="tags")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="comments")
    author: Mapped["User"] = relationship("User")
```

---

## Section 4 — Sessions and Queries

### Sync Session

```python
from sqlalchemy.orm import Session
from sqlalchemy import select

# Always use context manager!
with Session(engine) as session:
    # Create
    user = User(email="alice@example.com", hashed_password="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)   # reload from DB (gets auto-generated id)
    print(user.id)

    # Read one
    stmt = select(User).where(User.email == "alice@example.com")
    user = session.scalars(stmt).first()   # None if not found

    # Read one or raise
    user = session.get(User, 1)   # by primary key

    # Read many
    stmt = (
        select(User)
        .where(User.is_active == True)
        .order_by(User.created_at.desc())
        .offset(0)
        .limit(20)
    )
    users = session.scalars(stmt).all()

    # Update
    user.full_name = "Alice Smith"
    session.commit()

    # Delete
    session.delete(user)
    session.commit()
```

### Async Session (For FastAPI)

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,   # prevent lazy load after commit
)

# FastAPI dependency
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Usage
async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalars().first()

async def create_user(data: UserCreate, db: AsyncSession) -> User:
    user = User(email=data.email, hashed_password=hash_password(data.password))
    db.add(user)
    await db.flush()   # sends INSERT but doesn't commit (keeps transaction open)
    await db.refresh(user)
    return user
```

---

## Section 5 — Joins and Complex Queries

```python
from sqlalchemy import select, func, and_, or_

# Join
stmt = (
    select(Task, User)
    .join(User, Task.owner_id == User.id)
    .where(User.is_active == True)
)

# Filter with and_/or_
stmt = select(Task).where(
    and_(
        Task.priority >= 3,
        or_(
            Task.title.contains("urgent"),
            Task.is_complete == False,
        )
    )
)

# Count and aggregation
stmt = (
    select(User.id, func.count(Task.id).label("task_count"))
    .join(Task, Task.owner_id == User.id, isouter=True)  # LEFT JOIN
    .group_by(User.id)
    .having(func.count(Task.id) > 5)
    .order_by(func.count(Task.id).desc())
)

# Subquery
subq = (
    select(Task.owner_id)
    .where(Task.is_complete == False)
    .scalar_subquery()
)
stmt = select(User).where(User.id.in_(subq))
```

---

## Section 6 — The N+1 Problem and Eager Loading

### The N+1 Problem

```python
# BAD: N+1 query problem
users = session.scalars(select(User)).all()   # 1 query: SELECT * FROM users
for user in users:
    print(user.tasks)   # N queries: SELECT * FROM tasks WHERE owner_id = ?
# If 100 users → 101 queries!
```

### Fix with Eager Loading

```python
from sqlalchemy.orm import selectinload, joinedload, subqueryload

# selectinload: best for one-to-many (uses separate IN query)
stmt = (
    select(User)
    .options(selectinload(User.tasks))   # 2 queries total
)
users = session.scalars(stmt).all()
for user in users:
    print(user.tasks)   # no additional queries!

# joinedload: best for many-to-one (uses LEFT OUTER JOIN)
stmt = (
    select(Task)
    .options(joinedload(Task.owner))   # 1 query with JOIN
)
tasks = session.scalars(stmt).unique().all()

# Nested eager loading
stmt = (
    select(User)
    .options(
        selectinload(User.tasks).selectinload(Task.tags)   # users → tasks → tags
    )
)

# Detecting N+1: use echo=True on engine and count your queries
engine = create_engine(DATABASE_URL, echo=True)
```

### Confirm with `EXPLAIN ANALYZE` (PostgreSQL)

```python
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text(
        "EXPLAIN ANALYZE SELECT * FROM tasks WHERE owner_id = 1"
    ))
    for row in result:
        print(row[0])
# Look for: "Seq Scan" (bad on large tables) vs "Index Scan" (good)
```

---

## Section 7 — Alembic (Database Migrations)

### Setup

```bash
pip install alembic
alembic init alembic   # creates alembic/ directory and alembic.ini
```

Configure `alembic/env.py`:

```python
# alembic/env.py
from src.task_api.db import Base   # import your Base
from src.task_api.models import *  # import all models (so Base knows them)

target_metadata = Base.metadata

# For async:
def run_migrations_online():
    connectable = create_async_engine(DATABASE_URL)

    async def do_run_migrations(connection):
        await connection.run_sync(context.run_migrations)

    async def run_async_migrations():
        async with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            async with context.begin_transaction():
                await do_run_migrations(connection)

    asyncio.run(run_async_migrations())
```

### Creating and Running Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "add_users_table"

# Review the generated migration in alembic/versions/xxx.py !
# ALWAYS review before running

# Run migrations
alembic upgrade head       # apply all pending
alembic upgrade +1         # apply next one
alembic downgrade -1       # undo last one
alembic downgrade base     # undo all

# Check current state
alembic current
alembic history
```

### A Migration File (Always Review!)

```python
# alembic/versions/001_add_users_table.py
"""add users table

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2024-01-15
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

def downgrade() -> None:
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
```

### Data Migration

```python
# Migrate existing data (not just schema changes)
def upgrade() -> None:
    # 1. Add new column (nullable first)
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))

    # 2. Populate data
    op.execute("""
        UPDATE users
        SET full_name = first_name || ' ' || last_name
        WHERE first_name IS NOT NULL
    """)

    # 3. Make not nullable (after data is populated)
    op.alter_column("users", "full_name", nullable=False)

    # 4. Drop old columns
    op.drop_column("users", "first_name")
    op.drop_column("users", "last_name")
```

---

## Section 8 — Repository Pattern

A clean way to abstract your database queries:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Generic, TypeVar, Type

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: int) -> T | None:
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: T) -> None:
        await self.session.delete(obj)


class TaskRepository(BaseRepository[Task]):
    async def get_by_owner(self, owner_id: int) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.owner_id == owner_id)
            .options(selectinload(Task.tags))
            .order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_incomplete_high_priority(self) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.is_complete == False, Task.priority >= 4)
            .options(joinedload(Task.owner))
        )
        return list(result.scalars().unique().all())
```

---

## 🏋️ Exercises

### Exercise 1 — Full Data Model
Implement all models for the capstone project:
- `User`, `Task`, `Tag`, `Comment` with all relationships
- Write Alembic migrations for each
- Seed the DB with test data

### Exercise 2 — Find and Fix N+1
Write a route that lists tasks with their tags and owner.
Use `echo=True` to count queries. Fix the N+1 with `selectinload`.

### Exercise 3 — Data Migration
1. Add `first_name` and `last_name` to `User`
2. Write a migration that merges them into `full_name`
3. Test upgrade and downgrade

---

## ✅ Self-Check Questions

1. What is the difference between SQLAlchemy Core and ORM?
2. What is `Mapped[]` and why does SQLAlchemy 2.0 use it?
3. What does `cascade="all, delete-orphan"` do?
4. What is `selectinload` vs `joinedload`?
5. What is the N+1 problem and how do you detect it?
6. What does `expire_on_commit=False` do in `async_sessionmaker`?
7. What is the difference between `flush()` and `commit()`?
8. Why should you always review Alembic autogenerated migrations?
9. What does `pool_pre_ping=True` do?
10. What is the Repository pattern and what problem does it solve?

---

## 🔗 Key Links

- https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html
- https://alembic.sqlalchemy.org/en/latest/tutorial.html
- https://www.cosmicpython.com/
