# Chapter 3 – Asyncio Walk-Through

## Core Idea
This chapter is the technical heart of the book. It covers the Asyncio API from the ground up: coroutines, the event loop, tasks, futures, `async with`, `async for`, async generators, async comprehensions, and proper startup/shutdown handling.

---

## Quickstart — The 5 Things You Need

```python
import asyncio, time

async def main():
    print(f'{time.ctime()} Hello!')
    await asyncio.sleep(1.0)
    print(f'{time.ctime()} Goodbye!')

asyncio.run(main())
```

The 5 essential operations:
1. Start the event loop (`asyncio.run()`)
2. Define and call `async def` functions
3. Create tasks (`asyncio.create_task()`)
4. Wait for multiple tasks (`asyncio.gather()`)
5. Run blocking code in a thread (`loop.run_in_executor()`)

---

## The Tower of Asyncio (API Hierarchy)

| Tier | Concept | What you use |
|---|---|---|
| **Tier 9** | **Streams** | `StreamReader`, `StreamWriter`, `open_connection()`, `start_server()` |
| Tier 8 | Protocols | `Protocol` class |
| Tier 7 | Transports | `BaseTransport` |
| **Tier 6** | **Tools** | `asyncio.Queue` |
| **Tier 5** | **Executors** | `run_in_executor()` |
| **Tier 4** | **Tasks** | `asyncio.Task`, `create_task()` |
| Tier 3 | Futures | `asyncio.Future` |
| **Tier 2** | **Event loop** | `asyncio.run()`, `BaseEventLoop` |
| **Tier 1** | **Coroutines** | `async def`, `await`, `async with`, `async for` |

**Bold tiers = end-user developer focus.** The rest is mainly for framework designers.

---

## Coroutines

- An `async def` function is a **coroutine function** (not a coroutine itself)
- Calling it returns a **coroutine object**: `coro = f()`
- The event loop drives coroutines via `.send(None)` internally
- A coroutine "returns" by raising `StopIteration` with the return value
- Cancellation works by injecting `CancelledError` via `.throw()`
- **Always handle `CancelledError` cleanly** — never just absorb and continue

```python
async def main():
    try:
        while True:
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        # do cleanup, then let it propagate (or just let it exit)
        print("Cancelled, cleaning up...")
        raise  # re-raise is idiomatic
```

---

## Event Loop

- `asyncio.get_running_loop()` — **recommended**, callable only inside a coroutine
- `asyncio.get_event_loop()` — **discouraged** in modern code; works outside coroutines but confusing
- From Python 3.7+: use `asyncio.create_task(coro)` instead of `loop.create_task(coro)`

---

## Tasks and Futures

| | `Future` | `Task` |
|---|---|---|
| Represents | Any async completion state | A running coroutine |
| Created by | `asyncio.Future()` | `asyncio.create_task(coro)` |
| Result comes from | `.set_result(val)` | The coroutine's `return` value |
| Can be cancelled | Yes | Yes |

- **Use `create_task()`**, not `ensure_future()` — `ensure_future()` is a framework-designer utility
- `asyncio.gather(*tasks)` waits for all tasks concurrently and returns a list of results

---

## Async Context Managers: `async with`

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def web_page(url):
    data = await download_webpage(url)  # can await here
    yield data
    await update_stats(url)

async with web_page('google.com') as data:
    process(data)
```

- Use `@asynccontextmanager` (from `contextlib`) for simple cases
- For blocking code you can't modify, use `run_in_executor()` inside the context manager

---

## Async Iterators: `async for`

Requires the object to implement:
- `def __aiter__(self)` — returns `self`
- `async def __anext__(self)` — returns next value or raises `StopAsyncIteration`

```python
async for value in OneAtATime(redis, keys):
    await do_something_with(value)
```

---

## Async Generators (simpler!)

An `async def` function with `yield` = an **async generator** — much simpler than implementing `__aiter__`/`__anext__`:

```python
async def one_at_a_time(redis, keys):
    for k in keys:
        value = await redis.get(k)
        yield value

async for value in one_at_a_time(redis, keys):
    await process(value)
```

---

## Async Comprehensions

```python
result = [x async for x in async_generator()]           # list
result = {x: y async for x, y in async_generator()}     # dict
result = {x async for x in async_generator()}           # set
result = [await f(x) async for f, x in async_generator()]  # with await
```

---

## Startup and Shutdown

**The standard pattern:**
```python
async def main():
    # your app logic

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Bye!")
```

`asyncio.run()` automatically:
1. Collects all pending tasks
2. Cancels them (raises `CancelledError` inside each)
3. Gathers them with `return_exceptions=True`
4. Closes the loop

**Key rules:**
- Avoid creating new tasks inside `CancelledError` handlers — they won't be awaited by `asyncio.run()`
- Use `gather(*tasks, return_exceptions=True)` during shutdown so one failure doesn't abort the rest
- Handle `SIGTERM` in addition to `KeyboardInterrupt` in production services
- Once you receive a shutdown signal, **ignore subsequent signals** to prevent double-shutdown

---

## Blocking Code in Async Programs

**Never block the event loop.** For code you can't convert to async, use an executor:

```python
import asyncio

def blocking_io():
    time.sleep(1)  # this would freeze the event loop!
    return "done"

async def main():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, blocking_io)
```

---

## Key Takeaways
- `async def` functions return **coroutine objects** — they don't run until scheduled
- `await` marks where the event loop may switch to another coroutine
- Use `asyncio.run()` as the entry point — it handles loop lifecycle automatically
- Use `create_task()` to run coroutines concurrently; use `gather()` to wait for multiple
- Use `run_in_executor()` for any blocking code you can't make async
- Proper shutdown requires cancelling all tasks and waiting for them — `asyncio.run()` does this for you
- `async with`, `async for`, and async generators bring async support to familiar Python patterns
