# Chapter 2 – The Truth About Threads

## Core Idea
Threading is neither terrible nor perfect. It's a valuable tool — especially for CPU-bound parallelism — but carries real costs and hidden dangers for I/O-bound network programming. Understanding both its benefits and drawbacks is essential for choosing between threads and Asyncio.

---

## Benefits of Threading

| Benefit | Detail |
|---|---|
| **Simple mental model** | Code runs top-down and linearly; you can pretend concurrency isn't happening inside functions |
| **Parallelism with shared memory** | Multiple CPUs can share the same memory — important for numerical workloads |
| **Existing ecosystem** | Massive body of threaded libraries and best practices already exists |

**Best practice for safe threading:**
```python
from concurrent.futures import ThreadPoolExecutor as Executor

def worker(data):
    # process data — never touch global state!
    pass

with Executor(max_workers=10) as exe:
    future = exe.submit(worker, data)
```
- Use `ThreadPoolExecutor` (or `ProcessPoolExecutor` — same API) to manage threads safely
- Keep all required data passed *through* `submit()` — avoid global variables in threaded code

---

## Drawbacks of Threading

| Drawback | Detail |
|---|---|
| **Hard to reason about** | Bugs from preemptive context switching can be nearly impossible to reproduce |
| **Resource-intensive** | Each thread pre-allocates ~8 MB of virtual memory for its stack (10,000 threads → ~80 GB virtual memory) |
| **Throughput limit** | At very high concurrency (>5,000 threads), context-switching costs hurt throughput |
| **Inflexible scheduling** | The OS switches threads even when they're waiting idly, wasting CPU cycles |

---

## Case Study: Race Condition in Cutlery Tracking

A `ThreadBot` restaurant simulation demonstrates the core race condition problem:

```python
def change(self, knives, forks):
    self.knives += knives   # ⚠️ NOT ATOMIC
    self.forks += forks
```

`+=` internally compiles to three steps:
1. **Read** current value
2. **Add** new value
3. **Write** result back

If the OS switches threads between steps 1 and 3, one bot's update **overwrites** another's. The cutlery count ends up wrong.

**Test result:**
- 100 tables: ✅ passes (low contention)
- 10,000 tables: ❌ fails with wrong counts, and differently each run

**Fix:** Add a `threading.Lock` — but this requires knowing *every place* shared state is touched, which is extremely difficult in large codebases with third-party libraries.

---

## The Async Solution

Instead of adding locks everywhere, use a **single event loop (LoopBot)**: one thread doing all the work, switching between tasks at predictable `await` points.

> In async programs, **context switches are explicit** — they happen only at `await` keywords. No lock needed, because there's only one thread modifying state at a time.

---

## Key Takeaways
- Threading is appropriate for CPU-bound parallel work; Asyncio is better for I/O-bound concurrent work
- Race conditions in threaded code are the **hardest bugs to fix** — they're unpredictable and non-reproducible
- The best threading practice: use `ThreadPoolExecutor`, pass all data through `submit()`, avoid globals
- Asyncio solves the I/O-bound concurrency problem by making context-switch points **visible** with `await`
