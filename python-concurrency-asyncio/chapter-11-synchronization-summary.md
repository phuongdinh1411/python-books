# Chapter 11 – Synchronization

## Core Idea
asyncio's single-threaded model eliminates most thread race conditions, but it does **not** eliminate all concurrency bugs. Any shared state mutated across an `await` point can be corrupted. Chapter 11 introduces asyncio's synchronisation primitives — `Lock`, `Semaphore`, `Event`, and `Condition` — to coordinate coroutines safely.

---

## Single-Threaded Race Conditions

Even without multiple threads, shared state can be corrupted when one coroutine modifies it while another is suspended at `await`.

```python
user_sockets = {'Alice': socket_a, 'Bob': socket_b}

async def message_all():
    # Build message list — then we AWAIT
    messages = [send(sock, 'Hello') for _, sock in user_sockets.items()]
    await asyncio.gather(*messages)   # ← suspension point

async def disconnect(username):
    socket = user_sockets.pop(username)   # modifies shared dict
    socket.close()

# If disconnect('Alice') runs while message_all is awaiting gather:
# socket_a is closed, but we already prepared a send to it → crash!
await asyncio.gather(message_all(), disconnect('Alice'))
```

The key difference from threads: in asyncio, races only occur **at `await` points**; in threads, races can occur anywhere.

---

## `asyncio.Lock`

A lock ensures only one coroutine is in a critical section at a time.

```python
from asyncio import Lock

lock = Lock()

async def safe_section():
    async with lock:
        # only one coroutine runs here at a time
        await some_async_operation()
```

`async with lock` is equivalent to:
```python
await lock.acquire()
try:
    ...
finally:
    lock.release()
```

### Fix for the socket race above
```python
user_lock = Lock()

async def message_all(lock):
    async with lock:   # hold lock during entire send
        messages = [send(sock, 'Hello') for _, sock in user_sockets.items()]
        await asyncio.gather(*messages)

async def disconnect(username, lock):
    async with lock:   # wait for message_all to finish before closing
        socket = user_sockets.pop(username)
        socket.close()
```

### Watch out: don't create locks at module level
```python
# BAD — creates a new event loop at import time
lock = asyncio.Lock()

# GOOD — create inside an async context
async def main():
    lock = asyncio.Lock()
```
Python 3.10+ removes this footgun by deprecating the `loop` parameter on asyncio primitives.

---

## `asyncio.Semaphore` — Limiting Concurrency

A semaphore allows up to `N` coroutines in a section simultaneously. Useful for rate limiting API calls or capping DB connections.

```python
from asyncio import Semaphore

sem = Semaphore(10)   # max 10 concurrent HTTP requests

async def rate_limited_fetch(session, url):
    async with sem:
        async with session.get(url) as response:
            return await response.json()

# All 100 tasks run, but at most 10 hit the API simultaneously
tasks = [rate_limited_fetch(session, url) for url in urls]
await asyncio.gather(*tasks)
```

A `Lock` is a semaphore with `N=1`.

---

## `asyncio.Event` — Signalling Between Coroutines

An event is a one-time (or resettable) signal. Waiters block until the event is set.

```python
from asyncio import Event

event = Event()

async def waiter(name: str):
    print(f'{name} waiting...')
    await event.wait()        # blocks until event.set() is called
    print(f'{name} unblocked!')

async def setter():
    await asyncio.sleep(2)
    event.set()               # unblocks ALL waiters simultaneously

async def main():
    await asyncio.gather(waiter('A'), waiter('B'), setter())
```

Call `event.clear()` to reset it so waiters can block again.

| Method | Description |
|---|---|
| `event.set()` | Signal all waiters |
| `event.clear()` | Reset to unset state |
| `event.is_set()` | Check current state |
| `await event.wait()` | Block until set |

---

## `asyncio.Condition` — Conditional Wait

A `Condition` combines a lock and an event. It allows coroutines to wait for an arbitrary condition on shared state, and be notified when it might be true.

```python
from asyncio import Condition

condition = Condition()

async def worker(worker_id: int, items: list):
    async with condition:
        while not items:                     # spurious wakeups: always re-check
            await condition.wait()           # releases lock and waits
        item = items.pop()
    process(item)

async def producer(items: list):
    for item in source:
        async with condition:
            items.append(item)
            condition.notify()               # wake one waiter
            # condition.notify_all()         # wake all waiters

async def main():
    items = []
    await asyncio.gather(
        worker(1, items), worker(2, items),
        producer(items)
    )
```

### `notify` vs. `notify_all`
- `notify(n=1)` wakes `n` waiters.
- `notify_all()` wakes all waiters.

Always re-check the condition in a `while` loop — another coroutine may have consumed the item before you resumed.

---

## Synchronisation Primitives Summary

| Primitive | Purpose | Blocks until… |
|---|---|---|
| `Lock` | Mutual exclusion (1 at a time) | Lock released |
| `Semaphore(N)` | N-way concurrency cap | Semaphore count > 0 |
| `Event` | One-shot signal | Event set |
| `Condition` | Wait for arbitrary shared state | `notify` / `notify_all` called, then condition re-checked |

---

## Key Takeaway
asyncio's single-threaded model narrows the window for races, but shared mutable state across `await` points is still vulnerable. Use `Lock` when one coroutine at a time must own a resource. Use `Semaphore` to cap concurrency (rate limiting, connection pools). Use `Event` for simple go/no-go signalling. Use `Condition` when coroutines must wait for a complex state change. In most asyncio code you will rarely need these — the event loop's cooperative nature usually makes synchronisation unnecessary.
