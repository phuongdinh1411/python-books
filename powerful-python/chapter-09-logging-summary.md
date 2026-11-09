# Chapter 9 – Logging in Python

## Core Idea
Python's `logging` module is a well-designed, flexible, thread-safe system for recording application events. It's far superior to `print()` for any non-trivial program — providing severity levels, configurable destinations, and deferred string formatting.

## Key Concepts

### Log Levels (in order of increasing severity)
| Level | Function | Constant | When to use |
|---|---|---|---|
| DEBUG | `logging.debug()` | `logging.DEBUG` | Detailed diagnostic info |
| INFO | `logging.info()` | `logging.INFO` | Confirmation things work normally |
| WARNING | `logging.warning()` | `logging.WARNING` | Something unexpected, but still running |
| ERROR | `logging.error()` | `logging.ERROR` | A function failed |
| CRITICAL | `logging.critical()` | `logging.CRITICAL` | Program may not continue |

Default threshold: `WARNING` — debug and info are ignored unless you lower it.

### The Basic Interface (for scripts)
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.info("Server started on port %d", port)
logging.warning("Disk usage at %d%%", usage)
```
- `basicConfig()` must be called **once**, **before** any logging event, from the **main thread**
- Key options: `level`, `filename`, `filemode` (`"a"` append or `"w"` overwrite), `format`

### Passing Arguments (do it right)
```python
# ✅ Correct — string is formatted only if a log event actually fires
logging.info("We ate %d of your %s", num_fruits, fruit_name)

# ❌ Wrong — string is always formatted, wasting CPU/memory
logging.info(f"We ate {num_fruits} of your {fruit_name}")
logging.info("We ate %d of your %s" % (num_fruits, fruit_name))
```
F-strings and `%` formatting are always evaluated, even when the message is filtered out. The logging module defers formatting until it's actually needed.

### Logger Objects (for larger apps)
```python
logger = logging.getLogger()         # root logger
logger = logging.getLogger("myapp")  # named logger
logger.setLevel(logging.DEBUG)
```
- More flexible than the basic interface
- Support multiple destinations (handlers), each with its own level and format

### Handlers — Controlling Log Destinations
A **handler** routes log records to a specific destination:
```python
import logging, sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Console (stderr)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
logger.addHandler(console_handler)

# File (everything)
file_handler = logging.FileHandler("app.log")
logger.addHandler(file_handler)
```
- `StreamHandler` → stderr by default; pass `sys.stdout` for stdout
- `FileHandler` → writes to a file (appends by default)
- A logger can have **multiple handlers** with different levels
- A handler **cannot go below** the logger's own threshold — set the logger level to the lowest you need

### Formatters — Controlling Log Record Layout
```python
handler = logging.StreamHandler()
fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
handler.setFormatter(fmt)
```
Common format attributes:
| Attribute | Format | Description |
|---|---|---|
| `%(message)s` | string | The log message |
| `%(levelname)s` | string | DEBUG, INFO, WARNING, etc. |
| `%(name)s` | string | Logger name |
| `%(asctime)s` | string | Human-readable timestamp |
| `%(funcName)s` | string | Function containing the log call |
| `%(lineno)d` | int | Line number of the log call |
| `%(pathname)s` | string | Full path of the source file |

Note: Format strings use **percent-style** (`%(name)s`), not f-strings — by design for backward compatibility.

### Multi-Destination Pattern
```python
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)   # Must be the minimum across all handlers

console = logging.StreamHandler()
console.setLevel(logging.WARNING)  # Only warnings+ on screen
logger.addHandler(console)

logfile = logging.FileHandler("verbose.log")
# No setLevel → inherits DEBUG from logger
logger.addHandler(logfile)
```

## Key Takeaways
- Use `logging` instead of `print()` for anything beyond a quick script
- Choose log levels carefully — use them to communicate **severity and purpose**
- Always pass format arguments to the logging function (`logging.info("%s", val)`) — never pre-format the string
- For larger apps, use **logger objects** with **handlers** and **formatters** for full control
- Set the logger's `setLevel()` to the **lowest level** any handler needs; individual handlers can be more restrictive
- Use `logging.exception()` inside `except` blocks to capture the full stack trace automatically
