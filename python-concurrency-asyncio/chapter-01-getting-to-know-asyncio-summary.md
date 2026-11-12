# Chapter 1 – Getting to Know asyncio

## Core Idea
asyncio is Python's answer to high-concurrency I/O using **single-threaded cooperative multitasking**. One event loop drives many coroutines; each `await` is the only point where control passes to another task. Before diving into the API, Chapter 1 builds the mental model: what I/O-bound and CPU-bound actually mean, why threads have fundamental limits in CPython, and how non-blocking sockets make a single-threaded loop viable.

---

## I/O-Bound vs. CPU-Bound

| Work type | Time is spent in… | Asyncio helps? |
|---|---|---|
| **I/O-bound** | Waiting for network, disk, DB | ✅ Yes — await the wait |
| **CPU-bound** | Computation (math, parsing) | ❌ No — blocks the loop |

---

## Concurrency vs. Parallelism

- **Concurrency** — multiple tasks *in progress* at the same time (not necessarily running simultaneously). One thread can be concurrent.
- **Parallelism** — multiple tasks *executing* at the same physical instant; requires multiple CPU cores.
- asyncio provides **concurrency** (overlapping waits) not parallelism.

### Types of multitasking

| Type | Who decides to switch? | Example |
|---|---|---|
| **Preemptive** | OS scheduler | Threads |
| **Cooperative** | The code itself (`await`) | asyncio |

---

## Processes, Threads, and the GIL

**Process:** independent program with its own memory and at least one thread. Multiple processes = true parallelism on multi-core CPUs.

**Thread:** a unit of execution that shares memory with sibling threads. Python's GIL prevents more than one thread from executing Python bytecode at a time.

### The Global Interpreter Lock (GIL)
- CPython manages memory with **reference counting**. Reference counting is not thread-safe, so the GIL serialises bytecode execution.
- **Effect on CPU-bound threads:** two threads computing Fibonacci numbers in Python take almost *the same* time as one — the GIL forces them to take turns.
- **Effect on I/O-bound threads:** the GIL *is released* during I/O operations (network, disk). Two threads making HTTP requests **do** run faster together because each thread releases the GIL while waiting for the network.

```
# Fibonacci (CPU-bound): threads give NO speedup
fibs_no_threading() ≈ 65 s
fibs_with_threading() ≈ 66 s   ← actually slower due to thread overhead
```

```
# HTTP status codes (I/O-bound): threads DO help
sync two requests:   0.23 s
threaded two requests: ~0.12 s   ← GIL released during network wait
```

---

## How Single-Threaded Concurrency Works

### Sockets (brief intro)
A **socket** is a file-like object for network communication. By default sockets are **blocking** — `recv()` does not return until data arrives. Setting `socket.setblocking(False)` makes it raise an error immediately if no data is ready.

### The Event Loop
The event loop is a `while True` loop that:
1. Holds a set of tasks (coroutines) to run.
2. On each iteration, checks which tasks are ready (their I/O is complete).
3. Runs each ready task until it hits an `await` (yields control back).
4. Waits for I/O using the OS `select`/`epoll`/`kqueue` mechanism when nothing is ready.

```
while True:
    events = selector.select(timeout=None)   # block until something is ready
    for event in events:
        run_task_for(event)                  # run until the next await
```

This lets one thread handle thousands of connections — it never spins; it blocks the entire thread only when *all* tasks are waiting.

---

## Key Takeaway
asyncio targets **I/O-bound, high-concurrency** workloads. It does not speed up CPU-bound Python (use multiprocessing for that), does not bypass the GIL (it is single-threaded, so the GIL is irrelevant), and does not eliminate all race conditions (shared state modified across an `await` can still be inconsistent). Its power is **visible, explicit suspension points** that make reasoning about interleaving tractable.
