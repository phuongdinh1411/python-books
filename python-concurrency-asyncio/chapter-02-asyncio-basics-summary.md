# Chapter 2 – asyncio Basics

## Core Idea
Chapter 2 is the hands-on core of the asyncio API. It introduces coroutines, tasks, futures, and awaitables; shows how to create and cancel tasks; explains how to measure time; and warns about the two most common pitfalls (CPU-bound work and blocking library calls).

---

## Coroutines

### Defining and calling
```python
import asyncio

async def my_coroutine() -> int:
    return 42

# Calling returns a coroutine object — it does NOT run yet
coro = my_coroutine()       # <coroutine object my_coroutine at 0x…>
result = await coro         # now it runs; result = 42
```

`async def` defines a **coroutine function**. Calling it returns a **coroutine object**. The object runs only when `await`ed or scheduled as a task.

### `await` keyword
`await expr` suspends the current coroutine until `expr` completes, giving the event loop a chance to run other tasks. It can only be used inside an `async def` function.

### `asyncio.sleep`
`asyncio.sleep(n)` suspends the coroutine for `n` seconds *without blocking the thread*. This is the canonical way to simulate I/O in examples and to yield control to other tasks.

```python
async def countdown():
    for i in range(3, 0, -1):
        print(i)
        await asyncio.sleep(1)    # yields control; event loop can run other tasks
```

---

## Tasks

A **task** wraps a coroutine and schedules it to run on the event loop *concurrently* with the current coroutine — you do not need to `await` it immediately.

```python
async def main():
    task = asyncio.create_task(long_running_coroutine())
    # do other work here while long_running_coroutine runs concurrently
    result = await task   # wait for it when you need the result
```

### Running multiple tasks concurrently
```python
async def main():
    task1 = asyncio.create_task(delay(1))
    task2 = asyncio.create_task(delay(2))
    await task1
    await task2
# Total time ≈ 2 s, not 3 s
```

Key insight: both tasks are *scheduled* before either is awaited. The event loop interleaves them.

---

## Canceling Tasks and Setting Timeouts

### Canceling
```python
task = asyncio.create_task(long_task())
await asyncio.sleep(1)
task.cancel()           # sends CancelledError into the coroutine
try:
    await task
except asyncio.CancelledError:
    print('Task was cancelled')
```

### `asyncio.wait_for` — timeout with auto-cancel
```python
try:
    result = await asyncio.wait_for(coroutine(), timeout=1.0)
except asyncio.TimeoutError:
    print('Timed out!')
```
`wait_for` automatically cancels the coroutine when the timeout expires.

---

## Tasks, Coroutines, Futures, and Awaitables

| Type | Description |
|---|---|
| **Coroutine** | An `async def` function's return value; lowest-level |
| **Future** | A placeholder for a result that will arrive later |
| **Task** | A `Future` subclass that wraps and runs a coroutine |
| **Awaitable** | Anything you can `await` — coroutines, futures, and tasks |

### Futures
```python
from asyncio import Future

future = Future()
future.set_result(42)
result = await future   # 42
```

Rarely used directly in application code — `Task` is the preferred way to schedule work. Futures are building blocks for library authors.

### Relationship diagram
```
Awaitable
├── Coroutine object  (created by calling async def)
└── Future
    └── Task  (wraps a coroutine + schedules it)
```

---

## Measuring Time with Decorators

```python
import functools, time, asyncio

def async_timed():
    def wrapper(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                print(f'{func.__name__} took {elapsed:.4f} s')
        return inner
    return wrapper

@async_timed()
async def main():
    await asyncio.sleep(1)
```

---

## Pitfalls

### 1 — Running CPU-bound code
CPU-bound code **blocks the entire event loop** — all other tasks freeze.

```python
async def main():
    task1 = asyncio.create_task(cpu_heavy_work())   # blocks the loop!
    task2 = asyncio.create_task(delay(1))           # never gets a chance to run
    await asyncio.gather(task1, task2)
# task2 doesn't run until task1 finishes
```

Fix: offload CPU work to a process pool (see Chapter 6).

### 2 — Calling blocking library APIs (e.g., `requests`)
`requests.get()` blocks the OS thread; the event loop is frozen for the duration.

```python
async def bad():
    response = requests.get('https://example.com')  # ← blocks!
```

Fix: use async-native libraries (e.g., `aiohttp`) or offload to a thread pool executor.

---

## Event Loop Access

```python
# Preferred: let asyncio.run() manage the loop
asyncio.run(main())

# Manual (only needed for advanced use cases)
loop = asyncio.new_event_loop()
loop.run_until_complete(main())
loop.close()

# Access the running loop from inside a coroutine
loop = asyncio.get_running_loop()
```

---

## Debug Mode
Debug mode enables extra warnings (unawaited coroutines, slow callbacks, etc.):

```python
asyncio.run(main(), debug=True)          # via asyncio.run
# or
PYTHONASYNCIODEBUG=1 python app.py      # via environment variable
# or
python -X dev app.py                    # via command-line flag
```

---

## Key Takeaway
`create_task` is the core tool for overlapping I/O-bound work. Tasks run concurrently — but only between `await` points. Never put CPU-bound or blocking library calls in a coroutine without offloading them; they will freeze the event loop and negate all concurrency benefits.
