# Chapter 9 Summary: Asynchronous I/O
*High Performance Python, 3rd Edition*

---

## Core Problem: I/O-Bound Programs

When programs spend most of their time waiting on external data sources (network, disk, databases) rather than computing, they are called **I/O-bound**. For example, a 1ms network write could have spent that time executing **2.4 million CPU instructions** instead. This idle waiting is called **I/O wait**.

---

## Concurrency vs. Parallelism

| Concept | Description |
|---|---|
| **Concurrency** | Multiple tasks make progress over overlapping periods; async I/O often interleaves them on one thread |
| **Parallelism** | Multiple tasks execute simultaneously, for example across CPU cores (processes covered in Ch. 10) |

Concurrency is generally easier to reason about since all functions share the same memory space, but you still need to watch for **race conditions**.

---

## How Async I/O Works: The Event Loop

The runtime uses an **event loop** — a queue of functions to call. When a task hits I/O, it defers (yields) control back to the loop, which then runs another pending task. Two programming paradigms:

1. **Callbacks** — Pass a function to be called when the result is ready. Can lead to "callback hell."
2. **Coroutines / `async`/`await`** (modern, preferred) — Calling a coroutine function returns a **coroutine object**, not a `Future`. Await it or schedule it as a `Task`; tasks and futures represent completion. `await` may suspend execution while the loop runs other tasks.

Under the hood, `async`/`await` is built on Python **generators** — `await` is like `yield`, pausing and resuming execution.

---

## Web Crawler Example: Serial vs. Async

**Serial crawler** (`requests` library):
- 1,000 requests × 100ms delay = ~**102 seconds** total
- No overlap; each request blocks until complete

**Async crawler** (`aiohttp` + `asyncio.TaskGroup`):
- Same 1,000 requests completed in ~**1.33 seconds** — a **76× speedup!**
- aiohttp defaults to 100 concurrent connections; blocks of 100 requests each take ~100ms
- Optimal concurrency is typically **100–250 concurrent requests** — beyond that, diminishing returns set in as CPU overhead of context-switching takes over

---

## Mixed CPU + I/O Workload (bcrypt hashing → database saves)

Three approaches compared for a CPU task (bcrypt hashing) that saves results to a DB with 100ms response time:

### 1. Serial
- 600 iterations, difficulty 8: **70.6 seconds**
- 85% of runtime is pure I/O wait

### 2. Batched Async (`AsyncBatcher`)
- Accumulate N results, then flush them all concurrently with `asyncio.run()`
- Same workload: **10.21 seconds** — a **~7× speedup** with minimal code restructuring
- Good compromise: easy to add to existing serial code

### 3. Fully Async
- CPU tasks and I/O tasks interleaved via the event loop
- Key trick: `await asyncio.sleep(0)` inside the CPU loop — forces a yield to the event loop so queued I/O tasks can run
- Effectively **hides the I/O time** behind CPU time
- Result: **7.3× faster** than serial, **2× faster** on I/O than batched, and the benefit grows with more iterations
- Cooperative yields can improve responsiveness between small CPU chunks, but do not make computation nonblocking or parallel. For substantial CPU-bound Python work, use a process executor; choose a yield budget based on latency requirements rather than a universal 50–100ms rule.

---

## Key Takeaways

- Use async I/O when your program spends significant time waiting on external systems (networks, databases, files)
- The **`asyncio` + `aiohttp`** ecosystem provides modern, readable async patterns
- `asyncio.TaskGroup` (Python 3.11+) is the clean way to manage many concurrent tasks
- `asyncio.gather()` is an alternative to TaskGroup, useful when independent task failures shouldn't cancel others
- **Bound concurrency** with a semaphore or bounded worker queue; choose limits from service quotas, latency, memory, and measurements rather than a universal request count
- Intermediate solutions (batching) can give most of the benefit with less complexity
- For CPU-heavy work, full async + `multiprocessing` (Ch. 10) is needed to truly parallelize
