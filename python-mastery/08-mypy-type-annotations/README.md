# Pillar 8 — mypy & Type Annotations

> **Duration:** 1 week | **Priority:** 🟡 Medium-High

---

## 🎯 Learning Objectives

- Write fully-typed Python using modern syntax (3.10+)
- Use `TypeVar`, `Generic[T]`, `Protocol`, `TypedDict`, `Literal`, `overload`
- Configure and run `mypy --strict` with zero errors
- Understand the difference between static types and runtime behavior
- Apply types to FastAPI, SQLAlchemy, and pytest code

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [mypy Official Docs](https://mypy.readthedocs.io/) | 📄 Docs | ✅ Free |
| [Real Python Type Hints Guide](https://realpython.com/python-type-checking/) | 📄 Article | ✅ Free |
| [PEP 484 — Type Hints](https://peps.python.org/pep-0484/) | 📄 PEP | ✅ Free |
| [PEP 526 — Variable Annotations](https://peps.python.org/pep-0526/) | 📄 PEP | ✅ Free |
| [Python typing module docs](https://docs.python.org/3/library/typing.html) | 📄 Docs | ✅ Free |
| [mypy cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html) | 📄 Docs | ✅ Free |
| [pyright docs (Microsoft)](https://github.com/microsoft/pyright) | 📄 Docs | ✅ Free |

> 💡 **Optional paid book:** *Robust Python* — Patrick Viafore (O'Reilly)

---

## Section 1 — Type Annotation Basics

### Variables and Functions

```python
# Variables
name: str = "Alice"
age: int = 30
height: float = 1.75
active: bool = True

# Collections
names: list[str] = ["Alice", "Bob"]
scores: dict[str, int] = {"Alice": 95}
pair: tuple[int, str] = (1, "one")
unique: set[str] = {"a", "b"}

# Functions
def greet(name: str) -> str:
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    return a + b

def process(items: list[int]) -> dict[str, int]:
    return {"count": len(items), "sum": sum(items)}
```

### Optional and Union

```python
from typing import Optional

# Optional[T] = T | None
def find_user(user_id: int) -> Optional[str]:   # old style
    return None

def find_user(user_id: int) -> str | None:      # Python 3.10+ (preferred)
    return None

# Union: multiple possible types
def process(value: int | str | float) -> str:
    return str(value)

# Never return None implicitly — always annotate explicitly
def risky() -> str:
    pass   # mypy error: missing return statement
```

---

## Section 2 — `TypeVar` and `Generic`

TypeVar lets you write functions that work with multiple types while keeping type relationships.

```python
from typing import TypeVar, Generic

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# Generic function: input and output have the same type
def first(items: list[T]) -> T:
    if not items:
        raise IndexError("Empty list")
    return items[0]

first([1, 2, 3])          # returns int
first(["a", "b"])         # returns str
first([1.0, 2.0])         # returns float

# Bounded TypeVar: only subtypes of a given type
from numbers import Number
N = TypeVar("N", bound=Number)

def double(x: N) -> N:
    return x * 2   # type: ignore  (mypy limitation)


# Generic Class
class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        if not self._items:
            raise IndexError("Stack is empty")
        return self._items.pop()

    def peek(self) -> T:
        return self._items[-1]

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

# Usage:
int_stack: Stack[int] = Stack()
int_stack.push(1)
int_stack.push(2)
val: int = int_stack.pop()   # correctly typed as int

str_stack: Stack[str] = Stack()
str_stack.push("hello")
x: str = str_stack.pop()


# Generic Repository
class Repository(Generic[T]):
    def __init__(self, items: list[T] | None = None) -> None:
        self._items: list[T] = items or []

    def add(self, item: T) -> None:
        self._items.append(item)

    def get_all(self) -> list[T]:
        return self._items.copy()

    def find(self, predicate) -> T | None:
        return next((item for item in self._items if predicate(item)), None)
```

---

## Section 3 — `Protocol` (Structural Subtyping)

`Protocol` enables duck typing with static type checking.
No inheritance required — if it has the right methods, it's compatible.

```python
from typing import Protocol, runtime_checkable

class Drawable(Protocol):
    def draw(self) -> None: ...
    def resize(self, factor: float) -> None: ...

class Circle:
    def draw(self) -> None:
        print("Drawing circle")
    
    def resize(self, factor: float) -> None:
        self.radius *= factor

class Square:
    def draw(self) -> None:
        print("Drawing square")

    def resize(self, factor: float) -> None:
        self.side *= factor

# Circle and Square don't inherit from Drawable,
# but they satisfy the Protocol!

def render_all(shapes: list[Drawable]) -> None:
    for shape in shapes:
        shape.draw()

render_all([Circle(), Square()])   # mypy: OK!


# Runtime checkable Protocol
@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...

import io
f = io.StringIO()
print(isinstance(f, Closeable))   # True — runtime check works


# Practical: Comparable protocol
from typing import Protocol

class Comparable(Protocol):
    def __lt__(self, other: "Comparable") -> bool: ...
    def __eq__(self, other: object) -> bool: ...

CT = TypeVar("CT", bound=Comparable)

def find_min(items: list[CT]) -> CT:
    return min(items)

find_min([3, 1, 4, 1, 5])         # int
find_min(["banana", "apple"])      # str
```

---

## Section 4 — `TypedDict`, `Literal`, `Final`

### `TypedDict` — Typed Dictionaries

```python
from typing import TypedDict, Required, NotRequired

class UserDict(TypedDict):
    id: int
    email: str
    name: str

class UserDictOptional(TypedDict, total=False):
    # total=False makes all fields optional
    id: int
    email: str
    name: str

class UserMixed(TypedDict):
    id: int           # required (default)
    email: str        # required
    name: NotRequired[str]  # optional (Python 3.11+)

# Usage:
def process_user(user: UserDict) -> str:
    return f"{user['name']} ({user['email']})"

user: UserDict = {"id": 1, "email": "alice@example.com", "name": "Alice"}
process_user(user)   # mypy: OK
```

### `Literal` — Restrict to Specific Values

```python
from typing import Literal

TaskStatus = Literal["todo", "in_progress", "done"]
HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
LogLevel = Literal[1, 2, 3, 4, 5]

def set_status(task_id: int, status: TaskStatus) -> None:
    ...

set_status(1, "todo")        # OK
set_status(1, "invalid")     # mypy error!


def make_request(url: str, method: HttpMethod = "GET") -> dict:
    ...

make_request("/api/users", "POST")     # OK
make_request("/api/users", "TRACE")    # mypy error!
```

### `Final` — Constants

```python
from typing import Final

MAX_RETRIES: Final = 3
API_VERSION: Final[str] = "v1"
BASE_URL: Final = "https://api.example.com"

MAX_RETRIES = 5   # mypy error: cannot assign to Final
```

---

## Section 5 — `overload` — Multiple Signatures

```python
from typing import overload

@overload
def process(value: int) -> str: ...
@overload
def process(value: str) -> int: ...
@overload
def process(value: list[int]) -> list[str]: ...

def process(value):   # actual implementation (not type-checked)
    if isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        return int(value)
    elif isinstance(value, list):
        return [str(x) for x in value]

# mypy now understands:
result1: str = process(42)       # OK — int → str
result2: int = process("42")     # OK — str → int
result3: list[str] = process([1, 2, 3])  # OK
```

---

## Section 6 — `cast()` and `TYPE_CHECKING`

```python
from typing import cast, TYPE_CHECKING

# cast(): tell mypy to treat a value as a different type
# No runtime effect — purely for mypy
raw_data = get_config()   # returns Any
config = cast(dict[str, str], raw_data)   # treat as typed

# TYPE_CHECKING: import types only for static analysis
# Avoids circular imports and speeds up runtime
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

def process(session: "AsyncSession") -> None:   # forward reference
    ...

# Modern Python: use __future__ annotations for lazy evaluation
from __future__ import annotations   # at top of file — all annotations become strings
```

---

## Section 7 — `mypy` Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true            # enables all strict checks (recommended)

# What --strict enables:
# --disallow-untyped-defs      (all functions must be annotated)
# --disallow-any-generics      (no bare list, dict, etc.)
# --warn-return-any            (warn when returning Any)
# --warn-unused-ignores        (warn on unnecessary # type: ignore)
# --no-implicit-optional       (Optional must be explicit)
# ... and more

# Per-module overrides (for gradual adoption)
[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false   # relax rules for tests

[[tool.mypy.overrides]]
module = ["sqlalchemy.*", "alembic.*"]
ignore_missing_imports = true   # for untyped 3rd-party libs
```

```bash
# Run mypy
mypy src/

# Common flags
mypy --strict src/
mypy --ignore-missing-imports src/
mypy --show-error-codes src/      # show error codes like [return-value]
mypy --html-report htmlcov-mypy/  # HTML report
```

### Common mypy Errors and Fixes

```python
# Error: Argument 1 to "process" has incompatible type "Optional[str]"; expected "str"
def process(name: str) -> str:
    return name.upper()

user_name: str | None = get_name()
# Fix 1: add None check
if user_name is not None:
    process(user_name)
# Fix 2: provide default
process(user_name or "Unknown")

# Error: Return type "None" incompatible with declared return type "str"
def find(items: list[str], target: str) -> str:
    for item in items:
        if item == target:
            return item
    # mypy detects missing return for the "not found" case!
    # Fix:
    raise ValueError(f"{target!r} not found")
    # or: return ""

# Error: Need type annotation for "items" [var-annotated]
items = []              # mypy doesn't know what type!
items: list[str] = []  # Fix: annotate
```

---

## Section 8 — Types in Practice (FastAPI + SQLAlchemy)

### FastAPI with Full Types

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Annotated

app = FastAPI()

class TaskCreate(BaseModel):
    title: str
    priority: int = 1

class TaskResponse(BaseModel):
    id: int
    title: str
    priority: int
    model_config = {"from_attributes": True}

# Type alias for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[int, Depends(get_current_user)]

@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: DbSession,
    user_id: CurrentUser,
) -> TaskResponse:
    task = Task(title=task_data.title, priority=task_data.priority, owner_id=user_id)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return TaskResponse.model_validate(task)
```

### SQLAlchemy 2.0 — Already Typed

```python
from sqlalchemy.orm import Mapped, mapped_column

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Mapped[] already carries type info — no extra annotations needed!
```

---

## 🏋️ Exercises

### Exercise 1 — Type an Untyped Module
Take a module with no type annotations and add strict mypy to it.
Run `mypy --strict` until it passes with 0 errors.

### Exercise 2 — Generic Repository
Write a fully typed `Repository[T]` class that:
- Uses `Generic[T]` where `T` is bound to a `Base` model
- Has `get`, `get_all`, `create`, `update`, `delete` methods
- Passes `mypy --strict`

### Exercise 3 — Protocol Plugin System
Design a plugin system using `Protocol`:
- `DataParser` protocol with `parse(data: str) -> list[dict]`
- Implement: `JSONParser`, `CSVParser`, `XMLParser`
- Write a `run_parser(parser: DataParser, data: str)` function
- None of the parsers inherit from each other

---

## ✅ Self-Check Questions

1. What is the difference between `Optional[str]` and `str | None`?
2. What does `TypeVar` enable that regular types don't?
3. What is the key difference between Protocol and ABC (abstract base class)?
4. When would you use `TypedDict` over Pydantic's `BaseModel`?
5. What does `Literal["a", "b"]` do?
6. What does `Final` prevent?
7. When do you use `overload`?
8. What does `TYPE_CHECKING` guard against?
9. What does `mypy --strict` enable?
10. What is `Annotated` used for in FastAPI?

---

## 🔗 Key Links

- https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
- https://peps.python.org/pep-0484/
- https://docs.python.org/3/library/typing.html
- https://realpython.com/python-type-checking/
