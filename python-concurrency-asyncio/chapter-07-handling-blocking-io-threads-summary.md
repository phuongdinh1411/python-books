# Chapter 7 – Handling Blocking I/O with Threads

## Core Idea
Some libraries — `requests`, `boto3`, blocking file I/O, legacy database drivers — have no async counterpart. Running them directly in a coroutine freezes the event loop. Chapter 7 bridges async and sync worlds using `ThreadPoolExecutor`: blocking calls run in a thread, allowing the event loop to remain responsive. It also covers thread-specific synchronisation: locks, reentrant locks, semaphores, and how to pass results safely back to the event loop.

---

## The Problem: Blocking Libraries Freeze the Loop

```python
async def main():
    # requests.get blocks the OS thread — the entire event loop freezes
    response = requests.get('https://example.com')
```

---

## `ThreadPoolExecutor` + `run_in_executor`

```python
import asyncio
import concurrent.futures
import requests

def blocking_get(url: str) -> int:
    return requests.get(url).status_code

async def main():
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        status = await loop.run_in_executor(pool, blocking_get, 'https://example.com')
    print(status)

asyncio.run(main())
```

`run_in_executor(None, fn)` uses a default thread pool. Pass an explicit `ThreadPoolExecutor` for full control over pool size.

### Running many blocking calls concurrently
```python
async def main():
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        tasks = [
            loop.run_in_executor(pool, blocking_get, url)
            for url in urls
        ]
        results = await asyncio.gather(*tasks)
```

---

## `asyncio.to_thread` (Python 3.9+)

A convenience wrapper that runs a callable in the default thread pool:

```python
import asyncio

async def main():
    result = await asyncio.to_thread(blocking_get, 'https://example.com')
```

Equivalent to `loop.run_in_executor(None, fn, *args)` but more readable.

---

## Thread Safety and Race Conditions

Threads share memory, so a **read → `await` → write** sequence on shared state can race.

```python
# Classic race condition with threads
counter = 0

def increment():
    global counter
    current = counter          # read
    time.sleep(0.001)          # simulate work (switch may happen here)
    counter = current + 1      # write
    # if two threads both read 0, both write 1 — lost update
```

### `threading.Lock`
```python
import threading

lock = threading.Lock()
counter = 0

def safe_increment():
    global counter
    with lock:
        counter += 1    # atomic: only one thread in this block at a time
```

### Reentrant Lock (`threading.RLock`)
A regular `Lock` deadlocks if the same thread tries to acquire it twice (e.g., from a recursive function). `RLock` allows the same thread to acquire it multiple times:

```python
import threading

rlock = threading.RLock()

def recursive(n):
    with rlock:          # same thread can acquire multiple times
        if n > 0:
            recursive(n - 1)
```

---

## Deadlocks

A deadlock occurs when two threads each hold a lock the other needs and both wait forever.

```python
lock_a = threading.Lock()
lock_b = threading.Lock()

def thread_1():
    with lock_a:
        with lock_b:   # waits for lock_b
            ...

def thread_2():
    with lock_b:
        with lock_a:   # waits for lock_a → deadlock!
            ...
```

**Prevention:** always acquire locks in a consistent global order.

---

## `threading.Semaphore` — Limiting Concurrency

Semaphores cap how many threads can enter a section simultaneously:

```python
semaphore = threading.Semaphore(5)   # max 5 concurrent threads

def limited_work():
    with semaphore:
        requests.get(url)   # at most 5 concurrent HTTP requests
```

---

## Threading Queues for Producer–Consumer

`queue.Queue` is a thread-safe FIFO that decouples producers from consumers. Useful for GUI responsiveness: the main thread puts work on the queue; background threads process it.

```python
import queue, threading

work_queue = queue.Queue()

def worker():
    while True:
        item = work_queue.get()
        if item is None:
            break
        process(item)
        work_queue.task_done()

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()

for item in items:
    work_queue.put(item)

work_queue.join()   # wait for all items
for _ in threads:
    work_queue.put(None)   # poison pills to stop workers
```

---

## Mixing asyncio with Threads (Janus)

`janus` provides a queue that is safe from both thread-based and coroutine-based code:

```python
import asyncio, janus

async def main():
    queue = janus.Queue()

    def blocking_producer(sync_q):
        for item in data:
            sync_q.put(item)    # thread-safe put
        sync_q.put(None)

    async def async_consumer(async_q):
        while True:
            item = await async_q.get()   # async-safe get
            if item is None:
                break
            process(item)

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, blocking_producer, queue.sync_q)
    await async_consumer(queue.async_q)
```

---

## When to Use Threads vs. asyncio vs. Processes

| Scenario | Tool |
|---|---|
| Async-native I/O (aiohttp, asyncpg) | Coroutines + event loop |
| Blocking I/O, no async library | `ThreadPoolExecutor` + `run_in_executor` |
| CPU-bound Python code | `ProcessPoolExecutor` + `run_in_executor` |
| CPU-bound native code (NumPy) that releases the GIL | `ThreadPoolExecutor` is often sufficient |

---

## Key Takeaway
`ThreadPoolExecutor` + `run_in_executor` (or `asyncio.to_thread`) is the bridge between legacy blocking libraries and asyncio. Threads share memory — protect shared state with `threading.Lock` or `RLock`. Acquire locks in a consistent order to avoid deadlocks. Semaphores cap concurrency; `queue.Queue` decouples producers from consumers. Prefer async-native libraries when they exist; fall back to threads otherwise.
