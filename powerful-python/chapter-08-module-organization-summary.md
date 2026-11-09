# Chapter 8 – Module Organization

## Core Idea
Python's module system is flexible, powerful, and scales naturally from a single script to a large multi-file library. Understanding how to structure, refactor, and import modules is essential for writing maintainable, reusable code.

## Key Concepts

### Every `.py` File is a Module
- `findpattern.py` automatically creates a module named `findpattern`
- Anything `def`-ed or assigned at the top level is importable

### The Main Guard
When importing from a module, Python **executes the entire file**. Use a main guard to separate "library code" from "script code":
```python
if __name__ == "__main__":
    pattern, path = sys.argv[1], sys.argv[2]
    for line in grepfile(pattern, path):
        print(line)
```
- `__name__` equals `"__main__"` when the file is run directly
- `__name__` equals the module name (e.g., `"findpattern"`) when imported
- Without a main guard, importing a script that reads `sys.argv` will **crash**

### Creating Separate Libraries
- Extract reusable functions into a dedicated module (`greputils.py`) with no `if __name__ == "__main__"` — it's library-only
- Programs import from it: `from greputils import grepfile`
- Clear separation of roles: programs do things; libraries provide tools

### Multifile Modules (Package)
When a module grows too large, turn it into a **directory (package)**:
```
greputils/
    __init__.py
    files.py
    contain.py
```
- `__init__.py` defines what's importable from the top-level module
- Use **relative imports** inside `__init__.py`:
```python
# greputils/__init__.py
from .files import grepfile, igrepfile
from .contain import contains, icontains
```
- Now `from greputils import grepfile` still works — same interface, different implementation

### Import Syntax for Clean Diffs
Split multi-item imports across lines with trailing commas:
```python
from .files import (
    grepfile,
    igrepfile,
)
```
- Trailing comma = **one-line diffs** when adding a new item (no touching existing lines)
- Fewer merge conflicts; easier code reviews

### Nested Submodule Structure
Submodules can themselves be packages:
```
greputils/
    __init__.py
    files.py
    net/
        __init__.py   (or omit if empty in modern Python)
        html.py
        json.py
```
- Import from sub-submodules in `__init__.py` to maintain a flat public API
- Modern Python allows omitting empty `__init__.py` files

### `import *` — The Antipattern
```python
from greputils import *   # ⚠️ Never do this
```
**Problem:** If a future library upgrade adds a function with the same name, it **silently overrides** your existing function — a time bomb that may not detonate until production.

**Alternatives:**
```python
# Import specific names
from greputils import grepfile, contains

# Or import the module (namespaced)
import greputils
greputils.grepfile(...)

# Or alias for brevity
import greputils as gu
gu.grepfile(...)

# Or rename on import for clarity
from dateutil.parser import parse as parse_datetime
```

### Import Side Effects
- When Python imports a module, it **executes the entire file**
- Top-level code (not inside `def` or `class`) runs at import time
- **Avoid import-time side effects** (e.g., creating DB connections at the top level) — they are surprising, hard to control, and inflexible
- Use a factory function or explicit initialization call instead

## Key Takeaways
- Always use a **main guard** in files that double as scripts and modules
- Extract reusable code into its own **library module** early
- Grow a module into a **directory package** when it gets too large — the public import interface stays the same
- Use **trailing commas** and multi-line imports for cleaner diffs and fewer merge conflicts
- **Never use `import *`** — it creates silent name collision time bombs
- Avoid running significant code at import time — keep modules to definitions only
