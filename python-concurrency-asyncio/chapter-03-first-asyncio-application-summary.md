# Chapter 3 – A First asyncio Application

## Core Idea
Chapter 3 bridges the theory from chapters 1–2 with a real, working server. It starts with blocking sockets to show *why* they fail under concurrency, then builds up through non-blocking sockets and the `selectors` module, arriving at a proper asyncio echo server with graceful shutdown.

---

## The Problem with Blocking Sockets

A standard socket blocks the OS thread until data arrives or a connection is made. This means a server that handles two clients sequentially makes the second client wait until the first is completely finished.

```python
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', 8000))
server.listen()

conn, addr = server.accept()   # blocks until a client connects
data = conn.recv(1024)         # blocks until the client sends data
conn.sendall(data)             # echo it back
```

**Problem:** while waiting on `recv()` for client 1, client 2 cannot connect. One client can starve all others.

---

## Non-Blocking Sockets

`socket.setblocking(False)` makes calls raise `BlockingIOError` immediately instead of blocking when no data is available. This means the thread is never frozen waiting for a single socket.

```python
server.setblocking(False)

try:
    data = conn.recv(1024)
except BlockingIOError:
    pass   # no data yet; try other sockets
```

Non-blocking sockets alone require busy-polling (spinning in a loop checking every socket) — wasteful. The `selectors` module solves this.

---

## The `selectors` Module

`selectors.DefaultSelector` wraps the OS `select`/`epoll`/`kqueue` system call. You *register* sockets you are interested in and call `select()` — it blocks efficiently until at least one registered socket is ready.

```python
import selectors

sel = selectors.DefaultSelector()
sel.register(server_socket, selectors.EVENT_READ, data=None)

while True:
    ready = sel.select(timeout=None)    # block until something is ready
    for key, events in ready:
        if key.data is None:            # a new connection
            accept_connection(key.fileobj, sel)
        else:                           # data from an existing client
            handle_client(key, events, sel)
```

This is essentially a hand-built event loop — the exact mechanism asyncio uses internally.

---

## An asyncio Echo Server

asyncio provides `loop.sock_*` coroutines that wrap non-blocking sockets in awaitable form:

| Coroutine | Equivalent blocking call |
|---|---|
| `loop.sock_accept(server)` | `server.accept()` |
| `loop.sock_recv(conn, n)` | `conn.recv(n)` |
| `loop.sock_sendall(conn, data)` | `conn.sendall(data)` |

```python
import asyncio, socket

async def handle_client(conn: socket.socket):
    loop = asyncio.get_running_loop()
    try:
        while data := await loop.sock_recv(conn, 1024):
            await loop.sock_sendall(conn, data)
    finally:
        conn.close()

async def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(False)
    server.bind(('127.0.0.1', 8000))
    server.listen()

    loop = asyncio.get_running_loop()
    while True:
        conn, _ = await loop.sock_accept(server)
        asyncio.create_task(handle_client(conn))  # each client in its own task

asyncio.run(main())
```

Each client gets its own task. Tasks yield at every `await`, so the event loop freely interleaves all clients.

---

## Handling Errors in Tasks

If a task raises an exception and nobody awaits or inspects the result, the exception is **silently swallowed** (with only a warning at GC time).

```python
# Bad: exception lost
asyncio.create_task(bad_coroutine())

# Good: log or surface errors
def handle_exception(task: asyncio.Task):
    if not task.cancelled():
        exc = task.exception()
        if exc:
            logging.error('Task failed', exc_info=exc)

task = asyncio.create_task(bad_coroutine())
task.add_done_callback(handle_exception)
```

Always add a done callback or store the task reference and await it.

---

## Graceful Shutdown

A server needs to stop cleanly when it receives `SIGINT` (Ctrl+C) or `SIGTERM`. Raw `asyncio.run()` cancels pending tasks but doesn't give them a chance to finish.

### Strategy

1. Register a Unix signal handler with `loop.add_signal_handler`.
2. On signal: stop accepting new connections.
3. Gather all running client tasks and `await asyncio.gather(*tasks)` to let them finish.
4. Close the server socket.

```python
import signal

async def main():
    server = ...  # set up socket
    loop = asyncio.get_running_loop()
    tasks = set()

    def shutdown(signame):
        print(f'Received {signame}, shutting down')
        for task in tasks:
            task.cancel()

    loop.add_signal_handler(signal.SIGINT,  lambda: shutdown('SIGINT'))
    loop.add_signal_handler(signal.SIGTERM, lambda: shutdown('SIGTERM'))

    while True:
        conn, _ = await loop.sock_accept(server)
        task = asyncio.create_task(handle_client(conn))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
```

> **Note:** `loop.add_signal_handler` is Unix-only. On Windows use `signal.signal` instead.

---

## Key Takeaway
Sockets underpin every network library. Understanding the non-blocking socket → selectors → asyncio progression reveals *what the event loop is actually doing*. The pattern — create a task per connection, track tasks in a set, cancel and gather on shutdown — appears in every asyncio server you will ever write.
