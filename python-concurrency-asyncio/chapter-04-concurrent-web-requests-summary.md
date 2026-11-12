# Chapter 4 – Concurrent Web Requests

## Core Idea
Chapter 4 introduces `aiohttp` for async HTTP and then teaches the three main asyncio APIs for running multiple coroutines concurrently: `gather`, `as_completed`, and `wait`. Each has different trade-offs around exception handling, ordering, and cancellation.

---

## aiohttp Basics

`aiohttp` is an async-native HTTP client/server library. It replaces `requests` for asyncio programs.

```python
import aiohttp, asyncio

async def fetch_status(session, url: str) -> int:
    async with session.get(url) as response:
        return response.status

async def main():
    async with aiohttp.ClientSession() as session:
        status = await fetch_status(session, 'https://www.example.com')
        print(status)   # 200

asyncio.run(main())
```

### Asynchronous context managers
`async with` works like `with` but supports `__aenter__` / `__aexit__` coroutines, allowing setup and teardown to be non-blocking.

### Setting timeouts
```python
from aiohttp import ClientTimeout

timeout = ClientTimeout(total=1.0)   # 1-second total timeout
async with aiohttp.ClientSession(timeout=timeout) as session:
    ...
```

---

## `asyncio.gather` — Run All, Return All

`gather` takes an iterable of awaitables and runs them concurrently. It returns a list of results in the **same order** as the input.

```python
results = await asyncio.gather(
    fetch_status(session, 'https://example.com'),
    fetch_status(session, 'https://python.org'),
    fetch_status(session, 'https://aiohttp.readthedocs.io'),
)
# [200, 200, 200]  — always in input order
```

### Exception handling with gather
By default, if any awaitable raises, `gather` immediately propagates the exception and cancels the rest.

```python
# Suppress exceptions — get results OR exceptions per item
results = await asyncio.gather(*coroutines, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        print('Error:', result)
    else:
        print('Status:', result)
```

**When to use:** you need *all* results and their order matters, or you want a simple fan-out/fan-in.

---

## `asyncio.as_completed` — Process Results As They Arrive

`as_completed` wraps each awaitable in a task and yields futures in **completion order** (fastest first).

```python
import asyncio
from aiohttp import ClientSession

async def main():
    async with ClientSession() as session:
        requests = [fetch_status(session, url) for url in urls]
        for future in asyncio.as_completed(requests):
            status = await future
            print(f'Got status: {status}')   # printed as each response arrives
```

### With timeout
```python
for future in asyncio.as_completed(requests, timeout=2.0):
    try:
        status = await future
    except asyncio.TimeoutError:
        print('One request timed out')
```

**When to use:** you want to process results incrementally (e.g., update a progress bar, pipeline outputs).

---

## `asyncio.wait` — Fine-Grained Control

`wait` gives the most control. It takes a set of awaitables and returns two sets: `done` and `pending`.

```python
done, pending = await asyncio.wait(tasks, timeout=1.0)

for task in done:
    print(task.result())

for task in pending:
    task.cancel()
```

### Return conditions (`return_when` parameter)

| Constant | Returns when… |
|---|---|
| `ALL_COMPLETED` (default) | All tasks finish |
| `FIRST_COMPLETED` | Any one task finishes |
| `FIRST_EXCEPTION` | Any one task raises an exception |

```python
# Stop as soon as the first task finishes
done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
```

### Watching for exceptions
`wait` does **not** raise exceptions automatically. You must inspect each done task:
```python
done, _ = await asyncio.wait(tasks)
for task in done:
    if task.exception():
        print('Error:', task.exception())
    else:
        print('Result:', task.result())
```

### Always wrap coroutines in tasks first
`wait` requires tasks (not raw coroutines) to avoid surprising behaviour:
```python
tasks = [asyncio.create_task(coro) for coro in coroutines]
done, pending = await asyncio.wait(tasks)
```

---

## Comparison Table

| API | Order of results | Exception behaviour | Best for |
|---|---|---|---|
| `gather` | Input order | Raises immediately (or `return_exceptions=True`) | Fan-out + collect all |
| `as_completed` | Completion order | Raises per item as you iterate | Streaming / pipelines |
| `wait` | Unordered sets | Never raises; you inspect tasks | Fine-grained control, timeouts, partial completion |

---

## Key Takeaway
`gather` is the everyday workhorse. Use `as_completed` when you want to act on results as they arrive. Use `wait` when you need `FIRST_COMPLETED`/`FIRST_EXCEPTION` semantics or per-task exception inspection. Never forget to cancel `pending` tasks when you exit `wait` early — leaving them running is a resource leak.
