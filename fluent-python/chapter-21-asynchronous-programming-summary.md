# Chapter 21 – Asynchronous Programming

## Core Idea
`asyncio` uses a **single-threaded event loop** to handle thousands of concurrent I/O operations. Native coroutines (`async def` / `await`) are cooperative: they explicitly yield control when waiting for I/O, allowing other tasks to run. This makes async code efficient but requires that **blocking calls never appear in the event loop**.

## Core Concepts

| Term | Meaning |
|---|---|
| **Coroutine** | Function defined with `async def`; must be `await`ed |
| **Task** | A coroutine scheduled to run concurrently via `asyncio.create_task()` |
| **Awaitable** | Object that can be `await`ed: coroutines, tasks, futures |
| **Event loop** | Scheduler that runs tasks, handles I/O, and timers |

## Reading Async Code (Guido's Trick)
Mentally replace `await` with "return to event loop until ready, then resume here":
```python
async def probe(domain: str) -> tuple[str, bool]:
    loop = asyncio.get_running_loop()
    try:
        await loop.getaddrinfo(domain, None)  # suspend; other tasks run here
    except socket.gaierror:
        return domain, False
    return domain, True
```

## Task-Based Concurrency
```python
async def main():
    async with asyncio.TaskGroup() as tg:        # Python 3.11+
        t1 = tg.create_task(coro1())
        t2 = tg.create_task(coro2())
    # both tasks complete before here; exceptions propagate

# Older style:
tasks = [asyncio.create_task(coro(x)) for x in data]
results = await asyncio.gather(*tasks)
```

## Downloading with asyncio + HTTPX
```python
import asyncio, httpx

async def download_one(client: httpx.AsyncClient, cc: str, base_url: str):
    url = f'{base_url}/{cc.lower()}.gif'
    resp = await client.get(url, timeout=6.1, follow_redirects=True)
    return cc

async def download_all(ccs, base_url):
    async with httpx.AsyncClient() as client:
        tasks = [asyncio.create_task(download_one(client, cc, base_url)) for cc in ccs]
        return await asyncio.gather(*tasks)

asyncio.run(download_all(CC_LIST, BASE_URL))
```

## Throttling with Semaphores
```python
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def download_one(client, cc, semaphore):
    async with semaphore:   # limits concurrency
        return await client.get(url)
```

## `asyncio.as_completed`
Process results as each completes, not waiting for all:
```python
async def main():
    async with httpx.AsyncClient() as client:
        coros = [download_one(client, cc) for cc in ccs]
        for coro in asyncio.as_completed(coros):
            result = await coro
            process(result)
```

## Delegating to Executors (Blocking Code)
Never call blocking functions in the event loop. Offload to a thread executor:
```python
async def get_flag(client, cc):
    loop = asyncio.get_running_loop()
    img = await loop.run_in_executor(None, blocking_io_call, args)
    return img
```

## Asynchronous Context Managers and Iterators
```python
async with aiofiles.open('data.txt') as f:   # __aenter__ / __aexit__
    content = await f.read()

async for record in async_db_cursor:          # __aiter__ / __anext__
    process(record)

async def gen():
    for item in data:
        await asyncio.sleep(0)
        yield item   # async generator function
```

## Writing Async Servers
```python
# FastAPI
from fastapi import FastAPI
app = FastAPI()

@app.get('/flags/{cc}')
async def get_flag(cc: str):
    return await fetch_flag(cc)
```

## The All-or-Nothing Problem
You cannot `await` inside regular (non-async) functions. The moment you need async I/O, the entire call chain must be async. This is "What colour is your function?" — async and sync functions are incompatible in the calling direction.

## How asyncio Does NOT Work
- It is NOT magically concurrent for CPU-bound tasks
- Any **blocking call** (file I/O without asyncio, `time.sleep`, heavy computation) will **stall the event loop** and all other tasks
- asyncio only helps when the bottleneck is genuinely I/O waiting

## Closing Thoughts
`asyncio` shines for high-concurrency I/O: thousands of simultaneous network connections with minimal overhead compared to threads. The mental model is: all tasks share one thread; they take turns; you explicitly mark suspension points with `await`. The critical discipline is: **never block the event loop**. Use `run_in_executor` to offload blocking calls, and `asyncio.Semaphore` to throttle concurrency.
