# Chapter 18 – with, match, and else Blocks

## Core Idea
Context managers (`with`) are not just for file handling — they factor out any pair of setup/teardown operations. Pattern matching (`match/case`) brings powerful structural destructuring. `else` clauses on `for`, `while`, and `try` encode frequently misunderstood but useful control-flow idioms.

## Context Managers and `with`
The `with` statement calls `__enter__` on entry and guarantees `__exit__` on exit (even if an exception is raised):
```python
class LookingGlass:
    def __enter__(self):
        import sys
        self.original_write = sys.stdout.write
        sys.stdout.write = self.reverse_write
        return 'JABBERWOCKY'

    def reverse_write(self, text):
        self.original_write(text[::-1])

    def __exit__(self, exc_type, exc_val, exc_tb):
        import sys
        sys.stdout.write = self.original_write
        if exc_type is ZeroDivisionError:
            print('Please DO NOT divide by zero!')
            return True    # suppress the exception
        return False       # propagate all other exceptions
```
`__exit__` receives exception info; returning `True` suppresses it.

## `contextlib` Utilities
| Utility | Purpose |
|---|---|
| `@contextmanager` | Turn a generator into a context manager |
| `suppress(*exceptions)` | Silently ignore specified exceptions |
| `redirect_stdout(f)` | Temporarily redirect stdout |
| `ExitStack` | Manage a dynamic number of context managers |
| `AbstractContextManager` | ABC for context managers |

### `@contextmanager`
```python
from contextlib import contextmanager

@contextmanager
def looking_glass():
    import sys
    original_write = sys.stdout.write

    def reverse_write(text):
        original_write(text[::-1])

    sys.stdout.write = reverse_write
    msg = ''
    try:
        yield 'JABBERWOCKY'   # value given to 'as' variable
    except ZeroDivisionError:
        msg = 'Please DO NOT divide by zero!'
    finally:
        sys.stdout.write = original_write
        if msg:
            print(msg)
```
The `yield` is where the `with` block runs. Use `try/finally` (or `try/except`) around `yield` to handle exceptions from the block.

## Pattern Matching (`match/case`) — Case Study: `lis.py`
Ramalho uses a Scheme interpreter as an extended example:
```python
def evaluate(exp, env):
    match exp:
        case int(x) | float(x):      # numeric literal
            return x
        case str(var):               # variable lookup
            return env[var]
        case ['quote', x]:           # (quote x)
            return x
        case ['if', test, consequence, alternative]:
            if evaluate(test, env):
                return evaluate(consequence, env)
            else:
                return evaluate(alternative, env)
        case ['lambda', [*parms], *body]:
            return Procedure(parms, body, env)
        case ['define', str(name), value_exp]:
            env[name] = evaluate(value_exp, env)
        case [func_exp, *args]:       # function call
            proc = evaluate(func_exp, env)
            vals = [evaluate(a, env) for a in args]
            return proc(*vals)
```

### OR-patterns
```python
case ['quit'] | ['exit']:
    sys.exit()
```

### Guard clauses
```python
case [x, y] if x == y:
    print('equal pair')
```

## `else` Clauses Beyond `if`

### `for/else` and `while/else`
The `else` block runs only if the loop completed **without a `break`**:
```python
for item in collection:
    if predicate(item):
        break
else:
    # only if loop did not break — useful for "not found" logic
    raise ValueError('not found')
```

### `try/else`
The `else` block runs if **no exception** was raised in the `try` block:
```python
try:
    result = do_something()
except SomeError:
    handle()
else:
    # runs only on success; keep the "happy path" separate from exception handling
    process(result)
finally:
    cleanup()   # always runs
```
This separates: what you're trying to do (`try`), what might go wrong (`except`), what to do on success (`else`), and cleanup (`finally`).

## Closing Thoughts
`with` is more than file handling — it's a tool for factoring out setup/teardown pairs across tests, transactions, locks, redirections, and more. The `@contextmanager` decorator makes this accessible without writing a full class. `else` on loops and `try` encodes intent that would otherwise need a flag variable. Pattern matching restructures complex dispatch logic into readable, declarative cases.
