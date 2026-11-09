# Chapter 10 – Collaboration

## Core Idea
Writing Python for a team — or for others to use — requires discipline around packaging, documentation, API design, dependency management, and error handling. This chapter covers the tools and conventions that make collaborative Python codebases maintainable and safe.

## Items Summary

### Item 82: Know Where to Find Community-Built Modules
- **PyPI** (https://pypi.org) is the central repository of Python packages
- Install with: `python3 -m pip install <package>`
- Always prefer well-maintained community packages over reimplementing common functionality
- Check: download counts, GitHub stars, last release date, open issues, license
- Every PyPI package has a license — review it before using in commercial software

### Item 83: Use Virtual Environments for Isolated and Reproducible Dependencies
- System-wide `pip install` pollutes the global Python and breaks across projects
- **Virtual environments** isolate dependencies per project:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install requests
  ```
- `pip freeze > requirements.txt` — lock exact versions for reproducible installs
- Modern alternatives: **`uv`** (ultra-fast), **`poetry`**, **`pipenv`** — all manage venvs + lockfiles
- Always use a virtual environment — never install packages globally

### Item 84: Write Docstrings for Every Function, Class, and Module
- Python docstrings are accessible at runtime via `help()` and `.__doc__`
- Every public function, class, and module should have a docstring

**Module docstring**: purpose, main contents, usage example  
**Class docstring**: what the class represents, key attributes, usage pattern  
**Function docstring**: what it does, arguments (type + meaning), return value, exceptions raised

  ```python
  def find_anagrams(word: str, dictionary: list[str]) -> list[str]:
      """Find all anagrams of 'word' in 'dictionary'.

      Args:
          word: The word to find anagrams of.
          dictionary: List of candidate words to search.

      Returns:
          A list of words from 'dictionary' that are anagrams of 'word'.
          Returns an empty list if none are found.
      """
  ```
- Keep docstrings updated as code changes — stale docs are worse than no docs
- Use Google style, NumPy style, or reStructuredText consistently across the project

### Item 85: Use Packages to Organize Modules and Provide Stable APIs
- A **package** is a directory with `__init__.py` — it groups related modules
- Use `__init__.py` to expose the public API:
  ```python
  # mypackage/__init__.py
  from mypackage.models import User, Session  # re-export public types
  ```
- Use `__all__` to explicitly declare what `from package import *` exports:
  ```python
  __all__ = ["User", "Session"]
  ```
- Internal modules start with `_` (e.g., `_internal.py`) to signal "not public API"
- A clear `__init__.py` acts as a stable interface — internal restructuring doesn't break callers

### Item 86: Consider Module-Scoped Code to Configure Deployment Environments
- Use module-level code for environment-specific configuration:
  ```python
  # config.py
  import os
  DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
  DB_URL = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
  ```
- Import `config` everywhere — changes propagate automatically
- Avoid hardcoding environment-specific values in business logic
- For complex configs, consider `pydantic.BaseSettings` (auto-reads env vars with validation)

### Item 87: Define a Root Exception to Insulate Callers from APIs
- Callers who catch specific exceptions are coupled to your internal implementation
- Define a base exception class for your library; all your exceptions inherit from it:
  ```python
  class MyLibraryError(Exception):
      """Base class for all mylib errors."""

  class InvalidInput(MyLibraryError):
      pass

  class ResourceNotFound(MyLibraryError):
      pass
  ```
- Callers can catch `MyLibraryError` to handle all library errors generically
- Or catch specific subclasses for targeted handling
- When internal exceptions change, callers catching the base class are unaffected
- This is the foundation of a robust, stable public API

### Item 88: Know How to Break Circular Dependencies
- Circular imports (`a.py` imports `b.py`; `b.py` imports `a.py`) cause `ImportError` or partial modules
- **Solution 1: Reorder imports** — move one import inside a function (import on use):
  ```python
  def get_something():
      from . import other_module  # deferred import
      return other_module.thing
  ```
- **Solution 2: Restructure** — extract shared code into a third module that both can import without circularity
- **Solution 3: Import only what you need** — `from module import specific_name` is sometimes enough to break cycles
- Prefer restructuring (solution 2) as the permanent fix; deferred imports as a quick fix

### Item 89: Consider `warnings` to Refactor and Migrate Usage
- When deprecating API behavior, use `warnings.warn()` instead of breaking callers immediately:
  ```python
  import warnings

  def old_function(x, y=None):
      if y is not None:
          warnings.warn(
              "The 'y' parameter is deprecated; use 'z' instead.",
              DeprecationWarning,
              stacklevel=2,
          )
  ```
- `stacklevel=2` makes the warning point to the *caller's* line, not inside your library
- Filter categories in production: `warnings.filterwarnings("error")` turns warnings into errors in tests
- This gives callers time to migrate before you remove the deprecated API

### Item 90: Consider Static Analysis via `typing` to Obviate Bugs
- Type annotations + a typechecker (mypy, Pyright) find bugs before runtime
- Key annotation patterns:
  ```python
  from typing import Optional, Union, List, Dict, Tuple, Callable, TypeVar

  def process(items: list[int], callback: Callable[[int], bool]) -> list[int]:
      return [x for x in items if callback(x)]
  ```
- Gradually add annotations: start with function signatures, then internal variables
- Use `from __future__ import annotations` (Python 3.10+) to enable forward references easily
- Typecheckers as CI gates: fail builds when type errors are introduced

## Key Takeaways
- Always use virtual environments — never pollute global Python
- Document every public function, class, and module with a docstring
- Define a root exception class for every library you write
- Use `__all__` and `__init__.py` to define a stable public API
- Deprecate with `warnings.warn()`, not sudden breaks
- Use circular import restructuring (not hacks) as the permanent fix
- Adopt static type analysis via `mypy`/`pyright` — it's the best bang-for-buck in large codebases
