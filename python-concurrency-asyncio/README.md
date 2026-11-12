# Python Concurrency with asyncio — Learner Guide

[All books](../README.md)

## The Book in One Minute

**Main question:** how do you write Python applications that handle thousands of concurrent I/O operations efficiently, without the fragility of threads?

**Answer:** asyncio's cooperative multitasking model — one event loop, many coroutines, explicit `await` suspension points — lets you overlap I/O waits on a single thread. When I/O isn't enough, process pools handle CPU-bound work and thread pools bridge blocking libraries.

**Mental model:** the event loop is a `while True` that asks the OS "which sockets are ready?" and then runs the coroutine attached to each ready socket until it hits an `await`. Nothing between two `await` points in the same coroutine is ever interrupted — but shared state accessed across an `await` can still be stale.

**Coverage note:** these summaries follow Matthew Fowler's Manning book (14 chapters). Code was benchmarked on a 2019 MacBook Pro (i9, 32 GB) and a 32-core AWS c5ad.8xlarge. Your numbers will differ.

## Quick Route (About 45–60 Minutes)

1. [Ch. 1: Getting to know asyncio](chapter-01-getting-to-know-asyncio-summary.md) — I/O-bound vs CPU-bound, GIL, how the event loop works.
2. [Ch. 2: asyncio basics](chapter-02-asyncio-basics-summary.md) — coroutines, tasks, futures, cancellation, timeouts.
3. [Ch. 3: First application](chapter-03-first-asyncio-application-summary.md) — sockets to selectors to asyncio echo server + graceful shutdown.
4. [Ch. 4: Concurrent web requests](chapter-04-concurrent-web-requests-summary.md) — aiohttp, `gather`, `as_completed`, `wait`.
5. [Ch. 11: Synchronization](chapter-11-synchronization-summary.md) — single-threaded races, Lock, Semaphore, Event, Condition.

Chapters 1–4 are the technical heart; read them in order. Use chapters 5–14 as a reference menu based on your next real project.

## Chapter Map

| Chapter | What to retain |
|---|---|
| [1 — Getting to know asyncio](chapter-01-getting-to-know-asyncio-summary.md) | I/O-bound vs CPU-bound; GIL limits threads for CPU work; non-blocking sockets + selector = event loop |
| [2 — asyncio basics](chapter-02-asyncio-basics-summary.md) | `create_task` for concurrency; `wait_for` for timeouts; never put blocking code in a coroutine |
| [3 — First asyncio application](chapter-03-first-asyncio-application-summary.md) | Socket lifecycle; task-per-connection pattern; done callbacks for error visibility; graceful shutdown |
| [4 — Concurrent web requests](chapter-04-concurrent-web-requests-summary.md) | `gather` (all results, input order); `as_completed` (stream results); `wait` (fine control, partial completion) |
| [5 — Non-blocking database drivers](chapter-05-non-blocking-database-drivers-summary.md) | asyncpg, connection pools, async generators for large result sets, nested transactions |
| [6 — Handling CPU-bound work](chapter-06-handling-cpu-bound-work-summary.md) | `ProcessPoolExecutor` + `run_in_executor`; MapReduce; partition size trade-offs; shared state with locks |
| [7 — Handling blocking I/O with threads](chapter-07-handling-blocking-io-threads-summary.md) | `ThreadPoolExecutor` bridges blocking libs; `threading.Lock`, `RLock`; deadlock avoidance; `Janus` for async↔thread queues |
| [8 — Streams and network protocols](chapter-08-streams-and-network-protocols-summary.md) | `start_server`, `StreamReader`/`StreamWriter`; fan-out via tasks; Protocol API for low-level control |
| [9 — Web applications](chapter-09-web-applications-summary.md) | aiohttp server; ASGI vs WSGI; Starlette; Django async; WebSockets; 3× throughput over sync |
| [10 — Microservices and resilience](chapter-10-microservices-resilience-summary.md) | BFF pattern with `gather`; retry + exponential back-off; circuit breaker (Closed → Open → Half-open) |
| [11 — Synchronization](chapter-11-synchronization-summary.md) | asyncio races only at `await` points; Lock, Semaphore, Event, Condition |
| [12 — Asynchronous queues](chapter-12-asynchronous-queues-summary.md) | `asyncio.Queue` for producer–consumer; bounded queues for backpressure; background tasks in web apps; pub/sub |
| [13 — Managing subprocesses](chapter-13-managing-subprocesses-summary.md) | `create_subprocess_exec`; `communicate()` vs streaming; concurrent subprocesses with `gather`; timeouts |
| [14 — Advanced asyncio](chapter-14-advanced-asyncio-summary.md) | `sleep(0)` for cooperative loops; `ContextVar` for per-task state; `uvloop`; `call_soon`/`call_later` |

## Do Not Confuse

- **Coroutine function vs. coroutine object:** calling `async def fn()` returns a coroutine object — it does not run until `await`ed or wrapped in `create_task`.
- **Concurrency vs. parallelism:** asyncio gives you concurrent I/O on *one* thread. CPU-bound work needs `ProcessPoolExecutor` for real parallelism.
- **`gather` vs. `wait`:** `gather` raises on the first exception by default; `wait` never raises — you must inspect each task's `.exception()`. `gather` preserves input order; `wait` returns unordered sets.
- **`run_in_executor(None, fn)` vs. `ProcessPoolExecutor`:** `None` uses the default *thread* pool — good for blocking I/O but still GIL-limited for CPU work. Pass an explicit `ProcessPoolExecutor` for CPU-bound parallelism.
- **asyncio Lock vs. threading.Lock:** `asyncio.Lock` is `await`-based and only works inside coroutines. `threading.Lock` is blocking and used in regular threads. Never create an `asyncio.Lock` at module level (use inside an `async def`).
- **ASGI vs. WSGI:** WSGI has no `await`; it cannot support WebSockets or async frameworks. ASGI is the successor — use Uvicorn/Hypercorn as the ASGI server.
- **Bounded vs. unbounded queues:** an unbounded `asyncio.Queue` grows without limit if producers outrun consumers. Always set `maxsize` in production.

## Practice (15–25 Minutes)

Build a rate-limited URL fetcher with a bounded worker pool, a semaphore, and graceful error handling:

```python
import asyncio
import aiohttp

URLS = [f'https://httpbin.org/delay/{i % 3}' for i in range(12)]

async def fetch(session: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str) -> tuple[str, int]:
    async with sem:                               # max 3 concurrent requests
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                return (url, r.status)
        except asyncio.TimeoutError:
            return (url, -1)

async def main():
    sem = asyncio.Semaphore(3)
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(fetch(session, sem, url)) for url in URLS]
        for future in asyncio.as_completed(tasks):
            url, status = await future
            print(f'{status}  {url}')

asyncio.run(main())
```

Extend this: add retry logic with exponential back-off. Then add a circuit breaker that opens after 3 consecutive failures. Observe how `as_completed` interleaves results as each request finishes.

## Self-Check

1. Why does `asyncio.run(main())` not give you CPU parallelism even on a multi-core machine?
2. If `requests.get()` is called inside a coroutine, what happens to all other running tasks?
3. What is the difference between `asyncio.gather(*tasks, return_exceptions=True)` and a bare `gather`?
4. When is it safe to mutate shared state without a lock in asyncio?
5. Why should you set `maxsize` on a production `asyncio.Queue`?
6. What does `await asyncio.sleep(0)` accomplish that no sleep at all does not?

**Answer cues:**  
1. asyncio is single-threaded; use `ProcessPoolExecutor` for CPU parallelism.  
2. The entire event loop thread is blocked; no other tasks can run until `requests.get()` returns.  
3. `return_exceptions=True` puts exceptions in the result list instead of raising immediately; bare `gather` cancels remaining tasks and raises on first exception.  
4. Only when no `await` exists between the read and the write on that shared state.  
5. Without a bound, a slow consumer causes memory to grow without limit as the producer fills the queue.  
6. `sleep(0)` yields to the event loop for one iteration, allowing other tasks to run; no sleep skips the yield entirely.

**Next:** [Using Asyncio in Python](../using-asyncio-python/README.md) for a shorter, earlier treatment of the same topic from a different angle, or [High Performance Python, Ch. 10](../high-performance-python/chapter-10-multiprocessing-summary.md) for CPU-bound multiprocessing in depth.

---

## About This Book

**Title:** [Python Concurrency with asyncio](https://www.manning.com/books/python-concurrency-with-asyncio)  
**Author:** Matthew Fowler  
**Publisher:** Manning Publications, 2022  
**ISBN:** 9781617298660  
**Source code:** https://github.com/concurrency-in-python-with-asyncio
