# Using Asyncio in Python — Learner Guide

[All books](../README.md)

## The Book in One Minute

**Main question:** how can one thread coordinate many I/O operations without blocking on each one?

**Answer:** coroutine tasks cooperate with an event loop, suspending while async operations wait. Async-compatible libraries perform the actual I/O; task lifetime, timeouts, cancellation, and buffering make the system manageable.

**Mental model:** the event loop is one worker serving many jobs. Every job must return control promptly. `async def` alone does not make blocking code asynchronous.

The restaurant analogy is helpful for intuition, but it does not prove that asyncio is race-free or faster than every threaded design. This guide adds modern Python 3.11+ practices alongside the older API walkthrough.

## Quick Route (About 20–35 Minutes)

1. [Ch. 1: Introduction](chapter-01-introducing-asyncio-summary.md) — understand why overlapping waits helps.
2. [Ch. 2: Threads](chapter-02-truth-about-threads-summary.md) — distinguish preemptive from cooperative scheduling.
3. [Ch. 3: Walkthrough](chapter-03-asyncio-walkthrough-summary.md) — focus on `run`, coroutine objects, tasks, cancellation, and blocking-code bridges.
4. [Ch. 4: Libraries](chapter-04-asyncio-libraries-summary.md) — read Streams and the client relevant to your project.
5. [Ch. 5: Conclusion/history](chapter-05-concluding-thoughts-and-history-summary.md) — optional context after the practical material.

Do not memorize protocols/transports or manipulate coroutine `.send()`/`.throw()` as a first step. Those details mainly help framework authors.

## Chapter Map

| Chapter | What to retain |
|---|---|
| [1 — Introducing asyncio](chapter-01-introducing-asyncio-summary.md) | Visible suspension points and many concurrent I/O operations |
| [2 — Truth about threads](chapter-02-truth-about-threads-summary.md) | Threads remain useful; choose by libraries and bottleneck |
| [3 — Walkthrough](chapter-03-asyncio-walkthrough-summary.md) | Coroutines, tasks, loop lifetime, cancellation, async protocols |
| [4 — Libraries/case studies](chapter-04-asyncio-libraries-summary.md) | Streams, bounded queues, HTTP/DB clients, thread bridges |
| [5 — Conclusion/history](chapter-05-concluding-thoughts-and-history-summary.md) | Separate language syntax, event-loop library, and framework APIs |

## Five Distinctions to Remember

| Distinction | Practical consequence |
|---|---|
| Coroutine function vs. coroutine object vs. task | Calling `async def` creates an object; awaiting/scheduling drives it; a task tracks execution/completion |
| `await` vs. scheduling concurrent work | Awaiting each operation in a loop is sequential; schedule multiple tasks to overlap waits |
| `gather` vs. `TaskGroup` | `gather` returns ordered results; default failure propagation does not cancel siblings. `TaskGroup` scopes children and cancels siblings on ordinary child failure |
| Thread bridge vs. CPU parallelism | `to_thread` suits blocking I/O; an explicit process pool generally suits CPU-bound Python on GIL-enabled CPython |
| Single loop thread vs. race-free state | No task interleaving between suspension points; a read → await → write sequence can race |

## Practice (10–20 Minutes, Python 3.11+)

Run several simulated I/O jobs with bounded concurrency and a deadline:

```python
import asyncio

async def fetch(label, limit):
    async with limit:
        await asyncio.sleep(0.1)  # stands in for async I/O
        return label.upper()

async def main():
    limit = asyncio.Semaphore(2)
    async with asyncio.timeout(2):
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(fetch(label, limit))
                     for label in ("a", "b", "c", "d")]
    results = [task.result() for task in tasks]
    assert results == ["A", "B", "C", "D"]
    print(results)

asyncio.run(main())
```

Predict why four 0.1-second jobs with a limit of two take roughly two batches, not one. Compare with a sequential `await fetch(...)` loop. Then make one job raise `ValueError` and observe TaskGroup's exception group and sibling cancellation. Finally shorten the timeout and observe `TimeoutError` at the context boundary.

A semaphore limits active operations, not the number of task objects created. For millions of inputs, use a fixed worker count and a bounded queue instead.

## Production Checklist

- Reuse client sessions/connection pools; set request and overall deadlines.
- Use bounded queues or worker counts and choose a slow-consumer policy.
- Put cleanup in `finally`/context managers; close sockets and streams.
- Let `CancelledError` propagate after cleanup. Cancellation is cooperative and may not interrupt blocking calls or stop a thread already running.
- Keep CPU work and blocking I/O off the loop; `sleep(0)` is not a substitute for offloading substantial work.
- Design for retries, rate limits, dropped connections, and missed notifications; automatic reconnection is not durable delivery.

## Self-Check

1. Does `await` always switch tasks?
2. Why does replacing `requests.get` with an `async def` wrapper not solve blocking?
3. When does shared state need `asyncio.Lock`?
4. Why did a server created with only `asyncio.run(start_server(...))` exit immediately?

**Answer cues:** no, an awaitable may finish without suspension; synchronous call still occupies the loop; an invariant spans suspension points; loop ends after creation unless the main coroutine keeps serving.

**Next:** [High Performance Python, Ch. 9–10](../high-performance-python/README.md) for mixed I/O/CPU workloads and measured trade-offs.
