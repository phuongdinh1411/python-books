# Pillar 7 — pytest

> **Duration:** 1 week | **Priority:** 🟡 Medium-High

---

## 🎯 Learning Objectives

- Write clean, maintainable tests using pytest idioms
- Master fixtures: scopes, `conftest.py`, factories
- Use `@pytest.mark.parametrize` to eliminate test duplication
- Mock external dependencies with `pytest-mock` and `AsyncMock`
- Test async code with `pytest-asyncio`
- Achieve 90%+ coverage and interpret coverage reports
- Structure tests for a production FastAPI + SQLAlchemy application

---

## 📚 Resources

| Resource | Type | Priority |
|----------|------|----------|
| *Python Testing with pytest 2nd Ed* — Brian Okken | 📖 Book | Must |
| [pytest Official Docs](https://docs.pytest.org/) | 📄 Docs | Must |
| [Real Python pytest guide](https://realpython.com/pytest-python-testing/) | 📄 Article | Recommended |

---

## Section 1 — pytest Fundamentals

### Anatomy of a Test

```python
# tests/test_math_utils.py

def add(a: int, b: int) -> int:
    return a + b

# Convention: test file starts with test_
# Convention: test function starts with test_

def test_add_positive_numbers():
    # Arrange
    a, b = 2, 3

    # Act
    result = add(a, b)

    # Assert
    assert result == 5           # plain assert — pytest rewrites it for good errors

def test_add_negative_numbers():
    assert add(-1, -1) == -2

def test_add_zero():
    assert add(0, 5) == 5
```

```bash
pytest                      # run all tests
pytest tests/test_math.py   # run a specific file
pytest -v                   # verbose output
pytest -k "add"             # run tests matching "add"
pytest -x                   # stop on first failure
pytest --pdb                # drop into debugger on failure
pytest -s                   # show print() output
```

### Assert Introspection

```python
# pytest rewrites assert for detailed failure messages
def test_list_equality():
    result = [1, 2, 3, 4]
    expected = [1, 2, 3, 5]
    assert result == expected
    # Output:
    # AssertionError: assert [1, 2, 3, 4] == [1, 2, 3, 5]
    #   At index 3 diff: 4 != 5

def test_dict_subset():
    result = {"name": "Alice", "age": 30, "role": "admin"}
    assert result["name"] == "Alice"
    assert "role" in result
```

### Testing Exceptions

```python
import pytest

def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
        divide(1, 0)

def test_divide_by_zero_captures_exception():
    with pytest.raises(ZeroDivisionError) as exc_info:
        divide(1, 0)
    assert "zero" in str(exc_info.value).lower()
```

---

## Section 2 — Fixtures

Fixtures are the **most powerful** pytest feature. They set up and tear down state.

### Basic Fixture

```python
import pytest

class Database:
    def __init__(self):
        self.data = {}
        print("\nDB created")

    def close(self):
        print("\nDB closed")

@pytest.fixture
def db():
    database = Database()
    yield database       # test runs here
    database.close()     # teardown: runs after test

def test_insert(db):
    db.data["key"] = "value"
    assert db.data["key"] == "value"

def test_empty_start(db):
    assert len(db.data) == 0
```

### Fixture Scopes

```python
import pytest

@pytest.fixture(scope="function")   # default — new instance per test
def function_scope():
    return {"created": "per-test"}

@pytest.fixture(scope="class")      # one instance per test class
def class_scope():
    return {}

@pytest.fixture(scope="module")     # one instance per test file
def module_scope():
    return {}

@pytest.fixture(scope="session")    # one instance for the entire test run
def session_scope():
    return {}

# RULE: Use session scope for expensive setup (DB connection, app instance)
#       Use function scope for state that must be fresh each test
```

### `conftest.py` — Shared Fixtures

```python
# tests/conftest.py  ← automatically loaded by pytest
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.task_api.db import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()

@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncSession:
    """Provide a session that rolls back after each test."""
    async with async_engine.begin() as conn:
        session = AsyncSession(bind=conn)
        yield session
        await session.close()
        await conn.rollback()   # undo all changes after test

@pytest_asyncio.fixture
async def client(db_session):
    from httpx import AsyncClient, ASGITransport
    from src.task_api.main import app
    from src.task_api.deps import get_db

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

### Factory Fixtures

```python
# Using factory_boy for creating test data
# pip install factory-boy

import factory
from factory.alchemy import SQLAlchemyModelFactory
from src.task_api.models import User, Task

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    hashed_password = factory.LazyFunction(lambda: hash_password("password123"))
    full_name = factory.Faker("name")
    is_active = True

class TaskFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Task

    title = factory.Faker("sentence", nb_words=4)
    priority = factory.Faker("random_int", min=1, max=5)
    owner = factory.SubFactory(UserFactory)


# In tests:
def test_task_complete(db_session):
    UserFactory._meta.sqlalchemy_session = db_session
    user = UserFactory()
    task = TaskFactory(owner=user, is_complete=False)

    task.is_complete = True
    db_session.commit()

    assert task.is_complete is True
```

---

## Section 3 — Parametrize

Eliminate duplicated tests by parametrizing:

```python
import pytest

def is_valid_email(email: str) -> bool:
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

@pytest.mark.parametrize("email,expected", [
    ("user@example.com", True),
    ("user.name+tag@example.co.uk", True),
    ("invalid-email", False),
    ("@nodomain.com", False),
    ("no@tld", False),
    ("", False),
    ("user@.com", False),
])
def test_email_validation(email: str, expected: bool):
    assert is_valid_email(email) == expected


# Parametrize with IDs for readable output
@pytest.mark.parametrize("n,expected", [
    pytest.param(1, 1, id="fibonacci-1"),
    pytest.param(5, 5, id="fibonacci-5"),
    pytest.param(10, 55, id="fibonacci-10"),
])
def test_fibonacci(n: int, expected: int):
    assert fib(n) == expected


# Multiple parameters
@pytest.mark.parametrize("x", [1, 2, 3])
@pytest.mark.parametrize("y", [10, 20])
def test_multiply(x, y):
    assert x * y == x * y   # generates 6 test cases: (1,10), (1,20), (2,10)...
```

---

## Section 4 — Mocking with `pytest-mock`

```bash
pip install pytest-mock
```

### Basic Mocking

```python
from unittest.mock import MagicMock, patch, AsyncMock

# Method 1: mocker fixture (pytest-mock)
def test_send_email(mocker):
    mock_smtp = mocker.patch("src.notifications.smtplib.SMTP")

    from src.notifications import send_welcome_email
    send_welcome_email("user@example.com")

    mock_smtp.return_value.__enter__.return_value.sendmail.assert_called_once()


# Method 2: patch as decorator
@patch("src.notifications.smtplib.SMTP")
def test_send_email_decorator(mock_smtp):
    from src.notifications import send_welcome_email
    send_welcome_email("user@example.com")
    assert mock_smtp.called


# Method 3: patch as context manager
def test_send_email_context():
    with patch("src.notifications.smtplib.SMTP") as mock_smtp:
        from src.notifications import send_welcome_email
        send_welcome_email("user@example.com")
        mock_smtp.assert_called_once()
```

### Mocking Return Values and Side Effects

```python
def test_external_api(mocker):
    # Mock a function's return value
    mock_fetch = mocker.patch("src.services.fetch_user_data")
    mock_fetch.return_value = {"id": 1, "name": "Alice"}

    result = get_user_profile(1)
    assert result["name"] == "Alice"

def test_api_failure(mocker):
    # Mock a side effect (exception)
    mock_fetch = mocker.patch("src.services.fetch_user_data")
    mock_fetch.side_effect = ConnectionError("Service unavailable")

    with pytest.raises(ConnectionError):
        get_user_profile(1)

def test_multiple_calls(mocker):
    # Different return values on successive calls
    mock_roll = mocker.patch("random.randint")
    mock_roll.side_effect = [1, 2, 3, 4, 5]

    results = [roll_dice() for _ in range(5)]
    assert results == [1, 2, 3, 4, 5]
```

### Mocking Async Functions

```python
import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_async_service(mocker):
    # AsyncMock for async functions
    mock_fetch = mocker.patch("src.services.fetch_data", new_callable=AsyncMock)
    mock_fetch.return_value = {"data": "value"}

    result = await process_data(1)
    assert result == {"data": "value"}
    mock_fetch.assert_awaited_once_with(1)
```

### Spying on Real Functions

```python
def test_spy(mocker):
    # Calls the real function but also records calls
    spy = mocker.spy(src.services, "process_item")

    src.services.process_item(42)

    spy.assert_called_once_with(42)
    assert spy.call_count == 1
```

---

## Section 5 — Marks and Custom Markers

```python
import pytest

# Skip a test
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

# Skip conditionally
import sys
@pytest.mark.skipif(sys.platform == "win32", reason="Linux only")
def test_unix_feature():
    pass

# Expected failure
@pytest.mark.xfail(reason="Known bug — see issue #123")
def test_known_bug():
    assert buggy_function() == "expected"

# Custom marks (define in pyproject.toml or pytest.ini)
@pytest.mark.slow
def test_database_migration():
    pass

@pytest.mark.integration
def test_full_user_flow():
    pass
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

```bash
pytest -m "not slow"          # skip slow tests
pytest -m "unit"              # only unit tests
pytest -m "integration"       # only integration tests
```

---

## Section 6 — Coverage

```bash
pip install pytest-cov

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Output: htmlcov/index.html — interactive HTML report
```

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = ["src/*/migrations/*", "tests/*"]

[tool.coverage.report]
show_missing = true
fail_under = 85           # fail CI if coverage drops below 85%
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### What to Actually Test

```
Focus coverage efforts on:
  ✅ Business logic functions
  ✅ Edge cases (empty input, None, max values)
  ✅ Error paths (exceptions, 404s, 400s)
  ✅ Authentication and authorization
  ✅ Data transformations

Don't obsess over:
  ❌ 100% coverage on trivial getters/setters
  ❌ Testing framework code
  ❌ __repr__ methods
```

---

## Section 7 — Full API Test Suite Example

```python
# tests/test_tasks_api.py
import pytest
import pytest_asyncio
from httpx import AsyncClient

class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_task_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/tasks",
            json={"title": "Buy groceries", "priority": 2},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Buy groceries"
        assert data["priority"] == 2
        assert data["is_complete"] is False
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_task_missing_title(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/tasks",
            json={"priority": 2},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_unauthorized(self, client: AsyncClient):
        response = await client.post("/tasks", json={"title": "Test"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize("priority", [0, 6, -1, 100])
    async def test_create_task_invalid_priority(
        self, client: AsyncClient, auth_headers: dict, priority: int
    ):
        response = await client.post(
            "/tasks",
            json={"title": "Test", "priority": priority},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task_success(self, client: AsyncClient, task, auth_headers: dict):
        response = await client.get(f"/tasks/{task.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == task.id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/tasks/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_other_users_task(
        self, client: AsyncClient, other_user_task, auth_headers: dict
    ):
        response = await client.get(f"/tasks/{other_user_task.id}", headers=auth_headers)
        assert response.status_code == 403
```

---

## 🏋️ Exercises

### Exercise 1 — Parametrize a Parser
Write a CSV parser function and test it with 10+ parametrized cases covering:
- Normal rows, empty rows, quoted fields, missing columns, Unicode

### Exercise 2 — Mock an External API
Build a service that calls an external weather API.
Test it by mocking the HTTP call with `responses` library:
```bash
pip install responses
```

### Exercise 3 — Full API Test Suite
Write tests for the capstone Task API covering:
- All CRUD endpoints
- Auth: valid/invalid/expired tokens
- Pagination edge cases
- Concurrent requests (using `asyncio.gather`)

---

## ✅ Self-Check Questions

1. What is a fixture and what problem does it solve?
2. What are the 4 fixture scopes and when would you use each?
3. What does `yield` in a fixture do?
4. What is `conftest.py` and what goes in it?
5. How does `@pytest.mark.parametrize` reduce code duplication?
6. What is the difference between `MagicMock` and `AsyncMock`?
7. What does `mocker.spy` do differently from `mocker.patch`?
8. What does `--cov-report=term-missing` show?
9. How do you run only tests marked as `integration`?
10. What is `dependency_overrides` in FastAPI testing?

---

## 🔗 Key Links

- https://docs.pytest.org/
- https://pytest-mock.readthedocs.io/
- https://pytest-asyncio.readthedocs.io/
- https://coverage.readthedocs.io/
