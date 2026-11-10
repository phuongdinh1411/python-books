# Chapter 14 – Runtime Checking with pydantic

## Core Idea
Static typecheckers can't validate data that arrives at runtime from external sources (APIs, config files, databases). **pydantic** bridges this gap: it validates and parses incoming data at runtime using the same type annotations you already write.

## The Problem: External Data Is Untrusted
- Any data from outside your program (HTTP requests, env vars, JSON files, databases) may be invalid
- Manual validation logic (`if/else` checks) is verbose, error-prone, and hard to maintain
- The more validation logic you have, the harder it is to read and reason about

## Dynamic Configuration Example
Without pydantic, validating a config file looks like:
```python
def load_config(raw: dict) -> Config:
    if "host" not in raw:
        raise ValueError("Missing host")
    if not isinstance(raw["host"], str):
        raise TypeError("host must be a string")
    if raw["port"] < 1 or raw["port"] > 65535:
        raise ValueError("Invalid port")
    ...
```
This grows unwieldy fast.

## Version Note
The book-era examples use **Pydantic v1**. The examples below use **v2**: `field_validator`, `model_validate`, and `model_dump` replace common v1 APIs. For environment settings use the separate `pydantic-settings` package. Choose strict validation when coercion would hide invalid input; neither annotations nor a model prevent every later invalid mutation by default.

## pydantic Models
```python
from pydantic import BaseModel

class ServerConfig(BaseModel):
    host: str
    port: int
    debug: bool = False
```
- Inherit from `BaseModel`; declare fields with type annotations
- pydantic **validates and coerces** data automatically on instantiation:
  ```python
  config = ServerConfig(**raw_dict)  # raises ValidationError if invalid
  ```
- Invalid data raises a clear `ValidationError` with field-level detail

## Validators
Custom validation logic via `@field_validator` (v2; v1 used `@validator`):
```python
from pydantic import BaseModel, field_validator

class ServerConfig(BaseModel):
    port: int

    @field_validator("port")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v
```
- Validators are methods on the model — co-located with the data they validate
- Much more readable than scattered `if` checks

## Validation vs. Parsing
pydantic does both:
- **Validation**: reject bad data with a clear error
- **Parsing / coercion**: convert compatible types automatically  
  (`"42"` → `42` for an `int` field; `"true"` → `True` for a `bool` field)

This is sometimes called the **"parse, don't validate"** philosophy:
> Parse incoming data into a type with enforced boundary constraints. Internal code can then rely on those constraints **as long as later mutation and construction paths preserve them**; the static type system alone does not guarantee value validity.

## When to Use pydantic
- Configuration loading from files, environment variables
- API request/response models (FastAPI uses pydantic natively)
- Any boundary where untrusted data enters your system
- When you want validation logic co-located with the data model, not scattered across the codebase

## Closing Thoughts
pydantic reduces the cost of runtime validation by collapsing verbose `if/else` chains into declarative models. It shifts validation to the system boundary, so internal code can trust its data and focus on business logic. Combined with static typechecking, it covers both the static and dynamic aspects of type safety.
