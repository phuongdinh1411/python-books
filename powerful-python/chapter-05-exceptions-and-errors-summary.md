# Chapter 5 – Exceptions and Errors

## Core Idea
Python's exception system is much more than just error handling — it's a flexible flow-control tool. Understanding it deeply leads to more readable, more robust code, and faster debugging.

## Key Concepts

### The Basics
- Python **raises** exceptions (other languages say "throw")
- Use `try/except` to **handle** exceptions:
```python
try:
    message = describe_favorite("dessert")
except KeyError:
    print("No favorite dessert!")
```
- If no exception is raised, the `except` block is skipped entirely
- Once an exception is raised, execution jumps immediately to the matching `except` block

### Multiple `except` Clauses
```python
try:
    value = int(user_input)
except ValueError:
    logging.error("Bad value: %r", user_input)
except TypeError:
    logging.critical("Invalid type: %r", user_input)
```
- First matching `except` block runs; others are skipped
- **Rule of thumb**: put as little code as possible in the `try` block

### Exceptions for Flow Control
```python
try:
    from speedyjson import load
except ImportError:
    from json import load
```
Exceptions aren't just for errors — they're valid for controlling expected variations at runtime.

### `finally` Blocks
Runs **no matter what** — whether an exception is raised or not:
```python
try:
    fleet.start()
    running_job.wait()
finally:
    fleet.terminate()  # Always called, even on crash
```
Use `finally` for critical cleanup (closing files, releasing cloud resources, etc.)

### Exceptions as Objects
```python
try:
    show_element_info(['Ne', 'Ar', 'Br'])
except KeyError as err:
    missing = err.args[0]
    print(f"Missing element: {missing}")
```
- `err.args` is a tuple of constructor arguments
- Many exception types have specific attributes (e.g., `FileExistsError.filename`, `OSError.errno`)

### Raising Exceptions
```python
def positive_int(value):
    number = int(value)
    if number <= 0:
        raise ValueError(f"Bad value: {value}")
    return number
```
- Use `raise ExceptionClass(message)` to signal errors with informative messages
- `ValueError` = correct type, invalid value; `TypeError` = wrong type

### Catching and Re-Raising
```python
try:
    process_user_input(value)
except ValueError:
    logging.info("Invalid input: %s", value)
    raise  # re-raises the same exception
```
- `raise` alone (no arguments) re-raises the current exception
- Useful for logging at the source while letting higher-level code handle recovery

### ⚠️ The Most Diabolical Python Antipattern
```python
# NEVER DO THIS
try:
    do_something()
except:
    pass
```
This silently **hides all exceptions** — including bugs. A real-world example wasted **7 engineer-days** tracking down a bug that would have been fixed in 10 minutes without it.

**What to do instead:**
1. Catch a **specific exception**: `except ValueError: pass`
2. If you must catch broadly, **log the full stack trace**:
```python
try:
    do_something()
except Exception:
    logging.exception("Caught an error")  # logs message + full traceback
    raise  # propagate unless this boundary has a defined recovery policy
```
- `logging.exception()` records the full stack trace automatically
- Bare `except:` catches `BaseException`, including `KeyboardInterrupt` and `SystemExit`. `except Exception:` excludes those control-flow exceptions, but still needs a deliberate recovery or re-raise policy to avoid hiding bugs.

## Key Takeaways
- Handle specific exceptions, not broad ones — the more pinpointed, the better
- Use `finally` for code that must always run (resource cleanup, cloud billing, etc.)
- Capture exception objects with `as err` when you need details like the offending value
- `raise` (no args) inside an `except` block re-raises cleanly
- **Never use `except: pass`** — it buries bugs that could take days to find
- Use `logging.exception()` when you need to broadly catch and not re-raise
