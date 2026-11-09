# Chapter 4 – Constraining Types

## Core Idea
Basic annotations declare what *kind* of value something is. Constraining types goes further: **make illegal states unrepresentable**. If invalid combinations of data literally cannot be constructed, entire categories of bugs vanish.

## Six Constraining Techniques

### 1. `Optional[T]` (aka `T | None`)
- Use instead of bare `None` references — C.A.R. Hoare called null the "billion-dollar mistake"
- `Optional[str]` signals: "this may or may not have a value"
- Forces callers to explicitly handle the `None` case
- Replace `if x is not None:` patterns with `Optional` in signatures to make the possibility explicit

### 2. `Union[A, B]` (aka `A | B`)
- A value can be one of several types
- Use to model "either/or" scenarios without resorting to `Any`
- **Sum types**: `Union[str, int]` — a value is exactly one at a time
- **Product types** (data classes/namedtuples): combine multiple fields — a value has *all* at once
- Prefer `Union` over using `Any`; it constrains while still allowing flexibility

### 3. `Literal`
- Restrict a value to a specific set of constants:
  ```python
  def set_direction(dir: Literal["north", "south", "east", "west"]) -> None: ...
  ```
- Better than `str` alone; typechecker rejects any other string value
- Use when only a fixed set of values makes sense

### 4. `Annotated`
- Attach metadata to a type: `Annotated[int, ValueRange(0, 100)]`
- The metadata is ignored by the typechecker by default but can be used by runtime validators (e.g., pydantic)
- Documents constraints inline with the type

### 5. `NewType`
- Create a distinct type derived from an existing one:
  ```python
  UserId = NewType("UserId", int)
  ```
- `UserId` and `int` are incompatible from the typechecker's perspective
- Prevents accidentally passing a raw `int` where a `UserId` is expected
- Zero runtime cost — erased at runtime

### 6. `Final`
- Marks a variable as a constant that should never be rebound:
  ```python
  MAX_SIZE: Final = 100
  ```
- Communicates intent; typechecker flags any attempted reassignment
- Use for module-level constants and class-level configuration values

## Closing Thoughts
These tools progressively tighten the space of valid states your code can represent. Each constraint is documentation the typechecker can verify. The goal is a codebase where, if the code compiles cleanly, a large class of logical errors simply cannot exist.
