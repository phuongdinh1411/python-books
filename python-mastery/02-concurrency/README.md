# Pillar 2 — Concurrency

> **Duration:** 3 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Choose the right concurrency model for any problem (asyncio / threading / multiprocessing)
- Write production-quality `asyncio` code: coroutines, tasks, cancellation, timeouts
- Use `ThreadPoolExecutor` and `ProcessPoolExecutor` safely
- Bridge sync libraries into async code with `run_in_executor`
- Identify and fix: deadlocks, race conditions, blocking the event loop
- Implement common async patterns: producer-consumer, rate limiting, pub/sub

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [asyncio Official Docs](https://docs.python.org/3/library/asyncio.html) | 📄 Docs | ✅ Free |
| [Real Python: async IO in Python](https://realpython.com/async-io-python/) | 📄 Article | ✅ Free |
| [David Beazley — asyncio from scratch (PyCon 2015)](https://www.youtube.com/watch?v=MCs5OvhV9S4) | 🎥 Video | ✅ Free |
| [Real Python: Python Concurrency overview](https://realpython.com/python-concurrency/) | 📄 Article | ✅ Free |
| [threading docs](https://docs.python.org/3/library/threading.html) | 📄 Docs | ✅ Free |
| [multiprocessing docs](https://docs.python.org/3/library/multiprocessing.html) | 📄 Docs | ✅ Free |
| [concurrent.futures docs](https://docs.python.org/3/library/concurrent.futures.html) | 📄 Docs | ✅ Free |
| [David Beazley — Concurrency talks playlist](https://www.youtube.com/results?search_query=david+beazley+python+concurrency) | 🎥 Video | ✅ Free |

> 💡 **Optional paid book:** *Python Concurrency with asyncio* — Matthew Fowler (Manning)

---

## Choosing the Right Model

```
Is the bottleneck I/O (network, disk, DB)?
  ├── YES → asyncio (single-threaded, non-blocking) ← best default
  │          or threading (simpler but GIL limits CPU work)
  └── NO (CPU-bound: math, parsing, ML)
         └── multiprocessing (bypass the GIL with separate processes)

Rule of thumb:
  asyncio  → many concurrent I/O tasks, same process, event-driven
  threading → I/O-bound + legacy/blocking code you can't change
  multiprocessing → CPU-bound work, parallelism
```

---

## Section 1 — `threading`

### Basic Thread Usage

```python
import threading
import time

def download(url: str, results: list, index: int):
    print(f"[Thread-{index}] Fetching {url}")
    time.sleep(1)   # simulate I/O
    results[index] = f"data from {url}"

urls = ["http://a.com", "http://b.com", "http://c.com"]
results = [None] * len(urls)

threads = [
    threading.Thread(target=download, args=(url, results, i))
    for i, url in enumerate(urls)
]

for t in threads:
    t.start()
for t in threads:
    t.join()   # wait for all to finish

print(results)
```

### Thread Safety — Race Conditions

```python
import threading

counter = 0  # SHARED STATE — DANGEROUS!

def increment():
    global counter
    for _ in range(100_000):
        counter += 1   # NOT atomic: READ, ADD, WRITE

threads = [threading.Thread(target=increment) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()

print(counter)   # Expected: 500000, Actual: less due to race!
```

**Fix: Use a Lock**

```python
import threading

counter = 0
lock = threading.Lock()

def safe_increment():
    global counter
    for _ in range(100_000):
        with lock:   # only one thread at a time
            counter += 1

threads = [threading.Thread(target=safe_increment) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print(counter)   # Always 500000
```

### Locks, RLocks, Events, Semaphores

```python
import threading

# RLock — reentrant lock (same thread can acquire multiple times)
rlock = threading.RLock()

def recursive(n):
    with rlock:
        if n > 0:
            recursive(n - 1)   # would deadlock with regular Lock!

# Event — signal between threads
event = threading.Event()

def waiter():
    print("Waiting for signal...")
    event.wait()   # blocks until set()
    print("Got signal!")

def signaler():
    import time; time.sleep(2)
    event.set()

threading.Thread(target=waiter).start()
threading.Thread(target=signaler).start()

# Semaphore — limit concurrent access
semaphore = threading.Semaphore(3)  # max 3 concurrent

def limited_resource(i):
    with semaphore:
        print(f"Worker {i} using resource")
        import time; time.sleep(1)

threads = [threading.Thread(target=limited_resource, args=(i,)) for i in range(10)]
for t in threads: t.start()
for t in threads: t.join()
```

### `ThreadPoolExecutor` (Preferred for Pools)

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

def fetch(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read(100).decode()

urls = [
    "https://httpbin.org/get",
    "https://httpbin.org/ip",
    "https://httpbin.org/uuid",
]

with ThreadPoolExecutor(max_workers=3) as executor:
    # Submit all tasks
    futures = {executor.submit(fetch, url): url for url in urls}

    # Process as they complete
    for future in as_completed(futures):
        url = futures[future]
        try:
            result = future.result()
            print(f"{url}: {result[:50]}")
        except Exception as e:
            print(f"{url} failed: {e}")
```

---

## Section 2 — `multiprocessing`

### Basic Process Usage

```python
from multiprocessing import Process, Queue

def cpu_work(n: int, result_queue: Queue):
    # CPU-bound: runs in its own process with its own GIL
    result = sum(i * i for i in range(n))
    result_queue.put(result)

q = Queue()
processes = [
    Process(target=cpu_work, args=(10_000_000, q))
    for _ in range(4)
]

for p in processes: p.start()
for p in processes: p.join()

results = [q.get() for _ in processes]
print(results)
```

### `ProcessPoolExecutor` (Preferred)

```python
from concurrent.futures import ProcessPoolExecutor
import math

def heavy_compute(n: int) -> float:
    return sum(math.sqrt(i) for i in range(n))

numbers = [10_000_000] * 8  # 8 heavy tasks

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(heavy_compute, numbers))

print(results)
```

### Shared Memory (Python 3.8+)

```python
from multiprocessing import Process, shared_memory
import numpy as np

def modify_array(shm_name: str, shape: tuple, dtype):
    # Access existing shared memory from another process
    shm = shared_memory.SharedMemory(name=shm_name)
    arr = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
    arr[:] = arr * 2   # modify in-place
    shm.close()

# Create shared array
data = np.array([1, 2, 3, 4, 5], dtype=np.int64)
shm = shared_memory.SharedMemory(create=True, size=data.nbytes)
shared_arr = np.ndarray(data.shape, dtype=data.dtype, buffer=shm.buf)
shared_arr[:] = data   # copy data into shared memory

p = Process(target=modify_array, args=(shm.name, data.shape, data.dtype))
p.start()
p.join()

print(shared_arr)   # [2, 4, 6, 8, 10]
shm.close()
shm.unlink()   # free shared memory
```

---

## Section 3 — `asyncio` (The Most Important)

### Core Concepts

```
Coroutine   — a function defined with `async def`; can be paused and resumed
Awaitable   — anything you can `await`: coroutines, Tasks, Futures
Task        — a coroutine scheduled on the event loop (runs concurrently)
Event Loop  — the scheduler that runs coroutines, handles I/O events
```

### Your First Coroutines

```python
import asyncio

async def say_hello(delay: float, name: str) -> str:
    await asyncio.sleep(delay)   # non-blocking sleep
    msg = f"Hello, {name}!"
    print(msg)
    return msg

# Run a single coroutine
result = asyncio.run(say_hello(1.0, "World"))
print(result)
```

### Sequential vs Concurrent

```python
import asyncio
import time

async def fetch_data(source: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return f"data from {source}"

async def sequential():
    start = time.perf_counter()
    r1 = await fetch_data("API-1", 1.0)
    r2 = await fetch_data("API-2", 1.0)
    r3 = await fetch_data("API-3", 1.0)
    print(f"Sequential: {time.perf_counter() - start:.2f}s")   # ~3 seconds

async def concurrent():
    start = time.perf_counter()
    r1, r2, r3 = await asyncio.gather(
        fetch_data("API-1", 1.0),
        fetch_data("API-2", 1.0),
        fetch_data("API-3", 1.0),
    )
    print(f"Concurrent: {time.perf_counter() - start:.2f}s")   # ~1 second!

asyncio.run(sequential())
asyncio.run(concurrent())
```

### `asyncio.gather` vs `asyncio.create_task`

```python
import asyncio

async def work(n: int) -> int:
    await asyncio.sleep(1)
    return n * 2

async def with_gather():
    # Runs all coroutines concurrently, waits for all results
    results = await asyncio.gather(work(1), work(2), work(3))
    print(results)   # [2, 4, 6]

async def with_tasks():
    # Tasks start immediately when created
    t1 = asyncio.create_task(work(1))
    t2 = asyncio.create_task(work(2))

    # Can do other work here while tasks run...
    await asyncio.sleep(0.5)
    print("Tasks are running in background!")

    # Then wait for them
    r1 = await t1
    r2 = await t2
    print(r1, r2)   # 2, 4

asyncio.run(with_gather())
asyncio.run(with_tasks())
```

### Error Handling in `gather`

```python
import asyncio

async def risky(n: int) -> int:
    await asyncio.sleep(0.1)
    if n == 2:
        raise ValueError(f"n={n} is invalid!")
    return n

async def main():
    # return_exceptions=True: exceptions returned as results, not raised
    results = await asyncio.gather(
        risky(1), risky(2), risky(3),
        return_exceptions=True
    )
    for r in results:
        if isinstance(r, Exception):
            print(f"Error: {r}")
        else:
            print(f"Result: {r}")

asyncio.run(main())
```

### Timeouts and Cancellation

```python
import asyncio

async def slow_operation() -> str:
    await asyncio.sleep(10)
    return "done"

async def with_timeout():
    try:
        result = await asyncio.wait_for(slow_operation(), timeout=2.0)
    except asyncio.TimeoutError:
        print("Operation timed out!")

async def cancel_task():
    task = asyncio.create_task(slow_operation())
    await asyncio.sleep(1)

    task.cancel()   # Request cancellation
    try:
        await task
    except asyncio.CancelledError:
        print("Task was cancelled!")

asyncio.run(with_timeout())
asyncio.run(cancel_task())
```

### `asyncio.Semaphore` — Rate Limiting

```python
import asyncio
import aiohttp   # pip install aiohttp

async def fetch(session, url: str, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:   # only N requests at a time
        async with session.get(url) as response:
            return await response.text()

async def main():
    urls = [f"https://httpbin.org/delay/1?n={i}" for i in range(20)]
    semaphore = asyncio.Semaphore(5)   # max 5 concurrent requests

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

    print(f"Fetched {len(results)} pages")

asyncio.run(main())
```

### Producer-Consumer with `asyncio.Queue`

```python
import asyncio
import random

async def producer(queue: asyncio.Queue, n: int):
    for i in range(n):
        item = random.randint(1, 100)
        await queue.put(item)
        print(f"Produced: {item}")
        await asyncio.sleep(0.1)
    # Signal completion
    await queue.put(None)

async def consumer(queue: asyncio.Queue, name: str):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        print(f"[{name}] Consumed: {item}")
        await asyncio.sleep(0.3)
        queue.task_done()

async def main():
    queue = asyncio.Queue(maxsize=5)   # backpressure!
    
    prod = asyncio.create_task(producer(queue, 10))
    cons1 = asyncio.create_task(consumer(queue, "Consumer-1"))
    cons2 = asyncio.create_task(consumer(queue, "Consumer-2"))
    
    await asyncio.gather(prod, cons1, cons2)

asyncio.run(main())
```

### `run_in_executor` — Bridging Sync Code into Async

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time

def blocking_io() -> str:
    """A synchronous blocking function we can't change."""
    time.sleep(2)
    return "blocking result"

def cpu_heavy(n: int) -> int:
    """A CPU-intensive synchronous function."""
    return sum(i * i for i in range(n))

async def main():
    loop = asyncio.get_event_loop()

    # Run blocking I/O in thread pool (doesn't block event loop)
    with ThreadPoolExecutor(max_workers=3) as pool:
        result = await loop.run_in_executor(pool, blocking_io)
    print(result)

    # Run CPU work in process pool (bypasses GIL)
    with ProcessPoolExecutor(max_workers=2) as pool:
        result = await loop.run_in_executor(pool, cpu_heavy, 10_000_000)
    print(result)

asyncio.run(main())
```

### Async Context Managers and Iterators

```python
import asyncio

class AsyncDatabase:
    """Example async context manager."""

    async def __aenter__(self):
        print("Connecting to DB...")
        await asyncio.sleep(0.1)   # simulate connection
        return self

    async def __aexit__(self, exc_type, exc, tb):
        print("Closing DB connection...")
        await asyncio.sleep(0.1)
        return False

    async def query(self, sql: str):
        await asyncio.sleep(0.1)
        return [{"id": 1, "name": "Alice"}]


class AsyncRecordStream:
    """Example async iterator."""

    def __init__(self, records):
        self._records = records
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._records):
            raise StopAsyncIteration
        await asyncio.sleep(0.01)   # simulate streaming
        record = self._records[self._index]
        self._index += 1
        return record


async def main():
    async with AsyncDatabase() as db:
        rows = await db.query("SELECT * FROM users")

    stream = AsyncRecordStream(["a", "b", "c", "d"])
    async for record in stream:
        print(record)

asyncio.run(main())
```

### Lifespan Events (FastAPI pattern)

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def app_lifespan():
    """Setup and teardown for an application."""
    print("Starting up: connecting to DB, loading caches...")
    await asyncio.sleep(0.1)   # simulate startup
    
    yield   # app runs here
    
    print("Shutting down: closing connections...")
    await asyncio.sleep(0.1)   # simulate cleanup

async def main():
    async with app_lifespan():
        print("Application is running...")
        await asyncio.sleep(2)

asyncio.run(main())
```

---

## Section 4 — Common Pitfalls

### ❌ Blocking the Event Loop

```python
import asyncio, time

async def bad():
    time.sleep(2)   # BLOCKS the event loop! All other coroutines freeze.

async def good():
    await asyncio.sleep(2)   # Non-blocking, event loop continues

# Detection: use asyncio's debug mode
asyncio.run(bad(), debug=True)
# Shows: "Executing <Task> took 2.00 seconds"
```

### ❌ Forgetting to `await`

```python
import asyncio

async def fetch() -> str:
    return "data"

async def wrong():
    result = fetch()      # Returns a coroutine object, not the data!
    print(result)         # <coroutine object fetch at 0x...>

async def correct():
    result = await fetch()  # Actually runs the coroutine
    print(result)           # "data"
```

### ❌ Sharing State Without Locks

```python
import asyncio

counter = 0

async def unsafe_increment():
    global counter
    # Even in asyncio, concurrent tasks CAN have race conditions
    # at context switch points (between await statements)
    temp = counter
    await asyncio.sleep(0)   # yield — another task might run here!
    counter = temp + 1

async def safe_increment(lock: asyncio.Lock):
    global counter
    async with lock:
        temp = counter
        await asyncio.sleep(0)
        counter = temp + 1

async def main():
    global counter
    lock = asyncio.Lock()

    counter = 0
    await asyncio.gather(*[unsafe_increment() for _ in range(100)])
    print(f"Unsafe: {counter}")   # Likely not 100

    counter = 0
    await asyncio.gather(*[safe_increment(lock) for _ in range(100)])
    print(f"Safe: {counter}")     # Always 100

asyncio.run(main())
```

---

## Section 5 — `asyncio.TaskGroup` and `asyncio.timeout` (Python 3.11+)

### `asyncio.TaskGroup` — Structured Concurrency

`TaskGroup` is the modern, safer replacement for `asyncio.gather`. It guarantees
all tasks are cancelled and awaited if any task raises an exception.

```python
import asyncio

async def fetch(url: str) -> str:
    await asyncio.sleep(0.5)
    return f"data from {url}"

async def risky(n: int) -> int:
    if n == 2:
        raise ValueError(f"n={n} failed!")
    return n * 10

# OLD way (gather): exceptions don't cancel sibling tasks
async def old_way():
    results = await asyncio.gather(fetch("a"), fetch("b"), fetch("c"))
    return results

# NEW way (TaskGroup): if any task fails, ALL are cancelled
async def new_way():
    results = []
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("a"))
        t2 = tg.create_task(fetch("b"))
        t3 = tg.create_task(fetch("c"))
    # All tasks complete (or all are cancelled if one fails)
    return [t1.result(), t2.result(), t3.result()]

asyncio.run(new_way())

# TaskGroup raises ExceptionGroup when any task fails
async def handle_failure():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(risky(1))
            tg.create_task(risky(2))   # fails
            tg.create_task(risky(3))
    except* ValueError as eg:
        # except* (Python 3.11) handles ExceptionGroup
        for exc in eg.exceptions:
            print(f"Caught: {exc}")

asyncio.run(handle_failure())

# TaskGroup with dynamic tasks
async def process_many(items: list[str]) -> list[str]:
    results = {}
    async with asyncio.TaskGroup() as tg:
        for item in items:
            # Can create tasks inside the with block
            task = tg.create_task(fetch(item))
            results[item] = task
    return {k: t.result() for k, t in results.items()}
```

### `asyncio.timeout()` — Context-Manager Timeouts (3.11+)

```python
import asyncio

async def slow_db_query() -> str:
    await asyncio.sleep(5)
    return "result"

# OLD way
async def old_timeout():
    try:
        result = await asyncio.wait_for(slow_db_query(), timeout=2.0)
    except asyncio.TimeoutError:
        print("Query timed out")

# NEW way (more composable, can be shared across multiple awaits)
async def new_timeout():
    try:
        async with asyncio.timeout(2.0):
            result = await slow_db_query()
            # Could await multiple things within the same timeout budget
            other  = await another_query()
    except asyncio.TimeoutError:
        print("Query timed out")

# Deadline from an external context (e.g., request deadline)
async def with_deadline(deadline: float):
    async with asyncio.timeout_at(deadline):   # absolute time
        result = await slow_db_query()
```

---

## Section 6 — `anyio` — Backend-Agnostic Async (Worth Knowing)

`anyio` is an async compatibility layer that works on asyncio AND trio.
FastAPI and Starlette use it internally.

```bash
pip install anyio[asyncio,trio]
```

```python
import anyio

async def main():
    # Works identically on asyncio and trio backends
    async with anyio.create_task_group() as tg:
        tg.start_soon(fetch_data, "url1")
        tg.start_soon(fetch_data, "url2")

    # anyio timeout
    with anyio.fail_after(5):
        result = await slow_operation()

    # anyio sleep
    await anyio.sleep(1)

    # anyio thread-to-async bridge (like run_in_executor)
    result = await anyio.to_thread.run_sync(blocking_function, arg1)

# Run with asyncio backend (default for FastAPI)
anyio.run(main, backend="asyncio")

# Run with trio backend (for testing or if you prefer trio)
anyio.run(main, backend="trio")

# Why anyio matters:
# - FastAPI uses it → understanding anyio helps when writing FastAPI background tasks
# - Trio has better structured concurrency story than asyncio
# - anyio bridges the two worlds
```

---

## 🏋️ Exercises

### Exercise 1 — Concurrent Web Scraper
Build an async scraper using `aiohttp` that:
- Fetches 50 URLs concurrently
- Limits to 10 simultaneous connections with `asyncio.Semaphore`
- Retries failed requests up to 3 times
- Saves results to a JSON file

### Exercise 2 — Thread-Safe Cache
Implement a TTL (time-to-live) cache with:
- `threading.Lock` for thread safety
- Background thread that evicts expired entries
- `get(key)`, `set(key, value, ttl)`, `delete(key)` methods

### Exercise 3 — CPU Parallelism Benchmark
Write a script that:
- Computes a Mandelbrot set for a 1000x1000 grid
- Benchmarks: single-threaded, `ThreadPoolExecutor`, `ProcessPoolExecutor`
- Prints a comparison table

### Exercise 4 — Async Producer-Consumer Pipeline
Build a 3-stage pipeline with `asyncio.Queue`:
- Stage 1: reads lines from a file
- Stage 2: transforms each line (uppercase + strip)
- Stage 3: writes results to another file
- Multiple workers at each stage

---

## ✅ Self-Check Questions

1. When should you use `asyncio` vs `threading` vs `multiprocessing`?
2. What is the event loop, and what does it do?
3. What is the difference between a coroutine and a Task?
4. What does `asyncio.gather` do vs `asyncio.create_task`?
5. What happens if you call `time.sleep()` inside an async function?
6. How do you safely run a blocking function inside `asyncio`?
7. What is `asyncio.Semaphore` and when would you use it?
8. What is a deadlock? Give an example with threading.
9. How does `ProcessPoolExecutor` bypass the GIL?
10. What does `return_exceptions=True` do in `asyncio.gather`?

---

## 📖 Reading Checklist

- [ ] Python Concurrency with asyncio — Ch 1–4 (asyncio basics)
- [ ] Python Concurrency with asyncio — Ch 5–7 (Tasks, timeouts, streams)
- [ ] Python Concurrency with asyncio — Ch 8–9 (Connections, web apps)
- [ ] Real Python asyncio article
- [ ] Python threading docs
- [ ] Python multiprocessing docs
- [ ] Fluent Python Ch 19 — Concurrency Models in Python

---

## 🔗 Key Links

- https://docs.python.org/3/library/asyncio.html
- https://docs.python.org/3/library/threading.html
- https://docs.python.org/3/library/multiprocessing.html
- https://docs.python.org/3/library/concurrent.futures.html
- https://realpython.com/async-io-python/
