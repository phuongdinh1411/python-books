# Pillar 5 — FastAPI & Flask

> **Duration:** 2 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Build production-ready REST APIs with FastAPI
- Master FastAPI's dependency injection system
- Implement JWT authentication with OAuth2
- Understand Flask's request lifecycle and application factory pattern
- Write full test suites for both frameworks
- Deploy with lifespan events, middleware, and background tasks

---

## 📚 Resources

| Resource | Type | Priority |
|----------|------|----------|
| [FastAPI Official Docs](https://fastapi.tiangolo.com) | 📄 Docs | Must — do the full tutorial |
| [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template) | 💻 Repo | Must-read |
| [Flask Mega-Tutorial — Miguel Grinberg](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) | 📄 Tutorial | Must |
| [FastAPI Beyond CRUD (YouTube)](https://www.youtube.com/watch?v=sNgslEae9oc) | 🎥 Video | Recommended |

---

## ═══════════════════════════════════
## PART A — FastAPI
## ═══════════════════════════════════

## Section A1 — Project Setup

```bash
uv init task-api
cd task-api
uv add fastapi uvicorn[standard] pydantic httpx
uv add --dev pytest pytest-asyncio
```

```python
# src/task_api/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    print("Starting up: connecting to DB, warming caches...")
    # await db.connect()
    yield
    print("Shutting down: releasing resources...")
    # await db.disconnect()

app = FastAPI(
    title="Task API",
    description="A production-grade task management API",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

```bash
uvicorn src.task_api.main:app --reload
# Visit: http://localhost:8000/docs  ← auto-generated Swagger UI
# Visit: http://localhost:8000/redoc ← ReDoc UI
```

---

## Section A2 — Path, Query, and Body Parameters

```python
from fastapi import FastAPI, Path, Query, Body
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

app = FastAPI()

class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: TaskStatus = TaskStatus.todo
    priority: int = Field(default=1, ge=1, le=5)

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: int

    model_config = {"from_attributes": True}  # for ORM models


# Path parameter with validation
@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int = Path(..., ge=1, description="The task ID")
):
    # In real code: await db.get(task_id)
    return TaskResponse(id=task_id, title="Sample", status=TaskStatus.todo, priority=1)


# Query parameters
@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=5),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return []


# Request body
@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate):
    # In real code: await db.create(task)
    return TaskResponse(id=1, **task.model_dump())
```

---

## Section A3 — Dependency Injection (The Most Important Feature)

Dependency injection makes code **testable**, **composable**, and **DRY**.

```python
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

# ── Database Session Dependency ──────────────────────────────────
async def get_db() -> AsyncSession:
    """Provide a DB session for each request; always close it."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# ── Settings Dependency ──────────────────────────────────────────
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./test.db"
    secret_key: str = "changeme"
    debug: bool = False

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()

# ── Auth Dependency ───────────────────────────────────────────────
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt   # pip install pyjwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Using Dependencies in Routes ─────────────────────────────────
@app.get("/me")
async def get_me(
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # db and auth are automatically injected
    return {"user_id": current_user_id}
```

### Dependency Chains (Dependencies can depend on dependencies!)

```python
async def get_active_user(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user

async def get_admin_user(user: User = Depends(get_active_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    return user

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),   # chain: auth → active → admin
    db: AsyncSession = Depends(get_db),
):
    ...
```

---

## Section A4 — Routers (Organize Large Apps)

```python
# src/task_api/routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from ..deps import get_db, get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],  # apply to ALL routes in this router
)

@router.get("/")
async def list_tasks(): ...

@router.post("/", status_code=201)
async def create_task(): ...

@router.get("/{task_id}")
async def get_task(task_id: int): ...

@router.put("/{task_id}")
async def update_task(task_id: int): ...

@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int): ...


# src/task_api/main.py
from .routers import tasks, users, auth

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(users.router)
```

---

## Section A5 — Middleware

```python
import time
import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID to every request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.4f}s"
    return response


# CORS Middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## Section A6 — Error Handling

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class NotFoundError(Exception):
    def __init__(self, resource: str, id: int):
        self.resource = resource
        self.id = id

class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": f"{exc.resource} with id={exc.id} not found"},
    )

@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"error": exc.message})

# Usage in route:
@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    task = await find_task(task_id)
    if not task:
        raise NotFoundError("Task", task_id)
    return task
```

---

## Section A7 — Background Tasks

```python
from fastapi import BackgroundTasks

async def send_email(email: str, subject: str, body: str):
    """Non-critical: runs after response is sent."""
    import asyncio
    await asyncio.sleep(2)   # simulate email sending
    print(f"Email sent to {email}: {subject}")

async def log_activity(user_id: int, action: str):
    """Write to audit log asynchronously."""
    print(f"[AUDIT] User {user_id}: {action}")

@app.post("/tasks", status_code=201)
async def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: int = Depends(get_current_user),
):
    # Create task synchronously
    new_task = await db_create_task(task)

    # Schedule non-critical work for after response
    background_tasks.add_task(send_email, "user@example.com", "Task created", f"Task {new_task.id}")
    background_tasks.add_task(log_activity, current_user, f"created task {new_task.id}")

    return new_task   # response sent immediately!
```

---

## Section A8 — Testing FastAPI

```python
# tests/test_tasks.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from src.task_api.main import app
from src.task_api.deps import get_db, get_current_user

# Override the auth dependency for tests
async def override_auth():
    return 1   # always return user_id=1

# Override DB with a test DB
async def override_db():
    async with TestAsyncSession() as session:
        yield session

app.dependency_overrides[get_current_user] = override_auth
app.dependency_overrides[get_db] = override_db

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_task(client: AsyncClient):
    response = await client.post("/tasks", json={
        "title": "Write tests",
        "priority": 3,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Write tests"
    assert data["priority"] == 3

@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient):
    response = await client.get("/tasks/99999")
    assert response.status_code == 404
```

---

## ═══════════════════════════════════
## PART B — Flask
## ═══════════════════════════════════

## Section B1 — Application Factory Pattern

```python
# src/flask_app/__init__.py
from flask import Flask
from .extensions import db, migrate, jwt

def create_app(config_name: str = "default") -> Flask:
    """
    Application factory: creates and configures the Flask app.
    Allows creating multiple app instances (useful for testing).
    """
    app = Flask(__name__)

    # Load config
    from .config import config
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.tasks import tasks_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")

    # Register error handlers
    register_error_handlers(app)

    return app

def register_error_handlers(app: Flask):
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(e):
        return {"error": "Internal server error"}, 500
```

### Config

```python
# src/flask_app/config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///dev.db"

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
```

### Blueprint

```python
# src/flask_app/blueprints/tasks.py
from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Task

tasks_bp = Blueprint("tasks", __name__)

@tasks_bp.before_request
def require_auth():
    """Run before every request in this blueprint."""
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    verify_jwt_in_request()
    g.current_user_id = get_jwt_identity()

@tasks_bp.route("/", methods=["GET"])
def list_tasks():
    tasks = Task.query.filter_by(user_id=g.current_user_id).all()
    return jsonify([t.to_dict() for t in tasks])

@tasks_bp.route("/", methods=["POST"])
def create_task():
    data = request.get_json()
    task = Task(title=data["title"], user_id=g.current_user_id)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@tasks_bp.route("/<int:task_id>", methods=["GET"])
def get_task(task_id: int):
    task = Task.query.get_or_404(task_id)
    if task.user_id != g.current_user_id:
        return {"error": "Forbidden"}, 403
    return jsonify(task.to_dict())
```

---

## Section B2 — Testing Flask

```python
# tests/conftest.py
import pytest
from src.flask_app import create_app
from src.flask_app.extensions import db as _db

@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def db_transaction(app):
    """Wrap each test in a transaction and roll it back."""
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        _db.session.bind = connection
        yield
        transaction.rollback()
        connection.close()

# tests/test_tasks.py
def test_create_task(client, auth_headers):
    response = client.post(
        "/tasks/",
        json={"title": "Test task"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json["title"] == "Test task"

def test_unauthorized(client):
    response = client.get("/tasks/")
    assert response.status_code == 401
```

---

## FastAPI vs Flask — When to Choose

| | FastAPI | Flask |
|-|---------|-------|
| **Async support** | Native, first-class | Bolt-on (Flask 2.x) |
| **Performance** | Very fast | Good |
| **Type hints** | Required, powers everything | Optional |
| **Auto docs** | Built-in (Swagger + ReDoc) | Plugin needed |
| **Validation** | Pydantic (built-in) | Manual or Marshmallow |
| **Learning curve** | Moderate | Low |
| **Ecosystem** | Growing fast | Very mature |
| **Choose when** | New greenfield API, async I/O, ML serving | Existing codebase, simple apps, familiarity |

---

## Section A9 — WebSockets (FastAPI)

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Any
import json

app = FastAPI()

class ConnectionManager:
    """Manage active WebSocket connections with broadcast support."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.remove(ws)

    async def send(self, ws: WebSocket, message: dict) -> None:
        await ws.send_json(message)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)

manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(ws: WebSocket, client_id: str):
    await manager.connect(ws)
    await manager.broadcast({"type": "join", "user": client_id})
    try:
        while True:
            data = await ws.receive_json()
            # Echo back + broadcast to all
            await manager.broadcast({"type": "message", "from": client_id, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast({"type": "leave", "user": client_id})


# Test WebSocket with httpx
# pip install httpx[ws]
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_websocket():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.websocket_connect("/ws/alice") as ws:
            await ws.send_json({"text": "Hello"})
            msg = await ws.receive_json()
            assert msg["from"] == "alice"
```

---

## Section A10 — `httpx` Async Client (The Right Way to Call APIs)

```python
# Use httpx.AsyncClient with connection pooling (not httpx.get() — that creates new connection)
import httpx
from typing import Any

class APIClient:
    """Reusable async HTTP client with retry, timeout, and base URL."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def get(self, path: str, **params: Any) -> dict:
        response = await self._client.get(path, params=params)
        response.raise_for_status()   # raises HTTPStatusError on 4xx/5xx
        return response.json()

    async def post(self, path: str, data: dict) -> dict:
        response = await self._client.post(path, json=data)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "APIClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


# Usage in FastAPI (create once at startup, reuse across requests)
# In lifespan:
# app.state.api_client = APIClient("https://api.example.com", api_key="...")

# In a dependency:
# def get_api_client(request: Request) -> APIClient:
#     return request.app.state.api_client
```

---

## Section B3 — Flask + Server-Sent Events (SSE)

A lightweight alternative to WebSockets for one-way streaming (logs, progress, notifications).

```python
import time
from flask import Flask, Response, stream_with_context
import json

app = Flask(__name__)

def event_stream():
    """Generator that yields SSE-formatted data."""
    for i in range(10):
        data = json.dumps({"step": i, "total": 10, "message": f"Processing item {i}"})
        yield f"data: {data}\n\n"   # SSE format: "data: ...\n\n"
        time.sleep(0.5)
    yield "data: \"done\"\n\n"

@app.route("/stream")
def stream():
    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable Nginx buffering
        },
    )

# JavaScript client:
# const es = new EventSource('/stream');
# es.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## 🏋️ Exercises

### Exercise 1 — Full CRUD API (FastAPI)
Build a Task API with:
- `POST /auth/register` and `POST /auth/login` (returns JWT)
- Full CRUD for tasks (protected by JWT)
- Pagination on `GET /tasks`
- Background task: log creation events to a file

### Exercise 2 — Dependency Chain
Create a 3-level dependency chain:
1. `get_db` → provides DB session
2. `get_current_user(db)` → validates JWT, loads user from DB
3. `get_premium_user(user)` → checks user is on paid plan

### Exercise 3 — Flask Webhook Receiver
Build a Flask endpoint that:
- Receives GitHub webhook POST requests
- Validates HMAC-SHA256 signature
- Processes `push` and `pull_request` events
- Returns appropriate responses

---

## ✅ Self-Check Questions

1. What is FastAPI's dependency injection, and what problem does it solve?
2. How does `Depends` differ from directly calling a function?
3. What is the lifespan context manager used for?
4. What is a Pydantic `BaseModel` and why does FastAPI use it?
5. How do you override a dependency in tests?
6. What is the Flask application factory pattern and why use it?
7. What is a Blueprint in Flask?
8. How do `before_request` hooks differ from middleware?
9. What does `g` in Flask represent?

---

## 🔗 Key Links

- https://fastapi.tiangolo.com/tutorial/
- https://fastapi.tiangolo.com/advanced/
- https://flask.palletsprojects.com/en/3.0.x/
- https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world
