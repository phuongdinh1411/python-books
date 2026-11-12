# Chapter 14 – Advanced asyncio Topics

## Core Idea
Chapter 14 is for library authors and developers who need to go beyond the public asyncio API. It covers forcing event loop iterations, context variables for per-task state, and writing a custom event loop — revealing how asyncio works under the hood.

---

## Forcing Event Loop Iterations

The event loop only runs other tasks at `await` points. If you have a loop that never awaits, it blocks everything:

```python
async def cpu_loop():
    while True:
        do_some_work()   # never awaits — starves all other tasks
```

`await asyncio.sleep(0)` yields control for one iteration without sleeping:

```python
async def cooperative_loop():
    while True:
        do_some_work()
        await asyncio.sleep(0)   # yield to event loop; then resume immediately
```

This is the async equivalent of `threading.yield()`. Use it to make long-running coroutines cooperative.

---

## Context Variables (`contextvars`)

Threading uses `threading.local()` for per-thread storage. asyncio uses `contextvars.ContextVar` for **per-task** storage — each task gets its own copy of a context variable without interference.

```python
import asyncio
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar('request_id', default='none')

async def handle_request(rid: str):
    request_id.set(rid)          # set for this task's context only
    await asyncio.sleep(0.1)     # other tasks run here — no interference
    print(f'Request ID: {request_id.get()}')   # still correct

async def main():
    await asyncio.gather(
        handle_request('req-1'),
        handle_request('req-2'),
        handle_request('req-3'),
    )
    # Output: req-1, req-2, req-3 (in whatever order, but each sees its own value)

asyncio.run(main())
```

### Key APIs
```python
var = ContextVar('var', default=None)   # define
var.set(value)                          # set for current context
var.get()                               # get current context's value
token = var.set(value)                  # save token
var.reset(token)                        # restore previous value
```

### Use cases
- Request-scoped data in web frameworks (request ID, user, database session)
- Distributed tracing spans
- Locale / timezone settings per coroutine chain

---

## `asyncio.current_task()` and `asyncio.all_tasks()`

```python
# Get the currently running task
task = asyncio.current_task()
print(task.get_name())

# Get all tasks (useful for debugging or graceful shutdown)
tasks = asyncio.all_tasks()
for t in tasks:
    print(t.get_name(), t.done())
```

Assign names when creating tasks for easier debugging:

```python
task = asyncio.create_task(my_coro(), name='my-named-task')
```

---

## Writing a Custom Event Loop

asyncio's event loop is itself a Python class implementing `AbstractEventLoop`. You can replace it — Uvicorn uses `uvloop`, a Cython implementation that is significantly faster.

### Using `uvloop`
```python
import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
asyncio.run(main())   # now uses uvloop instead of the default loop
```

### Custom loop skeleton
```python
import asyncio

class CustomEventLoop(asyncio.SelectorEventLoop):
    """Extend the default selector-based loop."""

    def run_forever(self):
        print('Custom loop starting')
        super().run_forever()
        print('Custom loop stopped')

policy = asyncio.DefaultEventLoopPolicy()
policy._loop_factory = CustomEventLoop
asyncio.set_event_loop_policy(policy)
```

Writing a full event loop requires implementing `_run_once` (the core iteration), selector interaction, and all the scheduling primitives. Most developers should use `uvloop` rather than writing their own.

---

## `loop.call_soon` and `loop.call_later`

Low-level scheduling without coroutines. Useful for integrating non-async callbacks:

```python
loop = asyncio.get_event_loop()

def callback():
    print('called synchronously by the loop')

loop.call_soon(callback)             # run on next iteration
loop.call_later(2.0, callback)       # run after 2 seconds
loop.call_at(loop.time() + 2.0, callback)   # run at absolute loop time
```

These are building blocks for `asyncio.sleep` and other primitives.

---

## `loop.run_until_complete` vs `asyncio.run`

| | `asyncio.run(coro)` | `loop.run_until_complete(coro)` |
|---|---|---|
| Creates new loop | ✅ Always | Only if none exists |
| Closes loop on finish | ✅ Always | ❌ |
| Cancels pending tasks | ✅ | ❌ |
| Best for | Application entry points | Testing, frameworks |

Prefer `asyncio.run` in application code. Use `run_until_complete` only when you need to control the loop lifecycle yourself (e.g., test fixtures).

---

## Summary of Advanced Patterns

| Pattern | API | When to use |
|---|---|---|
| Yield to event loop | `await asyncio.sleep(0)` | Long CPU-ish coroutines that must stay cooperative |
| Per-task state | `contextvars.ContextVar` | Request IDs, tracing spans, locale |
| Custom loop | `uvloop`, `asyncio.set_event_loop_policy` | Need faster C event loop in production |
| Low-level callbacks | `loop.call_soon`, `loop.call_later` | Framework authors, integrating non-async code |
| Debug helpers | `asyncio.current_task()`, `asyncio.all_tasks()` | Debugging, graceful shutdown |

---

## Key Takeaway
`await asyncio.sleep(0)` makes long synchronous loops cooperative. `ContextVar` gives each task its own isolated state — the async alternative to thread-locals. Understanding `call_soon` / `call_later` demystifies how `asyncio.sleep` and `create_task` are implemented. For production performance, drop in `uvloop` with one line — it is a C-level event loop with the same API as the default Python one.
