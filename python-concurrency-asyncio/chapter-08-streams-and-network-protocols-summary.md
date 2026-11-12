# Chapter 8 – Streams and Network Protocols

## Core Idea
Chapter 8 moves beyond raw sockets to asyncio's higher-level **Streams API** — `asyncio.start_server` / `start_client`, `StreamReader`, and `StreamWriter`. It also introduces the lower-level **Protocol API** for full control. The running example is a multi-user chat server that fans messages out to all connected clients concurrently.

---

## asyncio Streams

The Streams API hides raw socket management behind two objects:

| Object | Role |
|---|---|
| `StreamReader` | Read bytes from a connection (non-blocking) |
| `StreamWriter` | Write bytes to a connection |

### Server
```python
import asyncio

async def handle_client(reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    print(f'Connected: {addr}')
    try:
        while data := await reader.read(1024):
            writer.write(data)          # echo back
            await writer.drain()        # flush the buffer
    except asyncio.IncompleteReadError:
        pass
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8000)
    async with server:
        await server.serve_forever()

asyncio.run(main())
```

### Client
```python
async def tcp_client():
    reader, writer = await asyncio.open_connection('127.0.0.1', 8000)
    writer.write(b'Hello\n')
    await writer.drain()
    data = await reader.read(1024)
    print(f'Received: {data.decode()}')
    writer.close()
    await writer.wait_closed()
```

### Key `StreamReader` methods

| Method | Description |
|---|---|
| `read(n)` | Read up to `n` bytes |
| `readline()` | Read until `\n` |
| `readexactly(n)` | Read exactly `n` bytes or raise `IncompleteReadError` |
| `readuntil(separator)` | Read until separator byte sequence |

---

## Multi-User Chat Server

A chat server needs to:
1. Accept connections and track all active users.
2. On each message from a user, fan it out to every *other* user concurrently.

```python
import asyncio

users: dict[str, asyncio.StreamWriter] = {}

async def broadcast(sender: str, message: str):
    for username, writer in users.items():
        if username != sender:
            writer.write(f'{sender}: {message}\n'.encode())
            await writer.drain()

async def handle_client(reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter):
    username = (await reader.readline()).decode().strip()
    users[username] = writer
    print(f'{username} joined')
    try:
        while line := await reader.readline():
            asyncio.create_task(broadcast(username, line.decode().strip()))
    finally:
        del users[username]
        writer.close()
        print(f'{username} left')

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8000)
    async with server:
        await server.serve_forever()

asyncio.run(main())
```

Each incoming message spawns a broadcast task so the client coroutine doesn't block waiting for slow recipients.

---

## asyncio Protocol API (Lower Level)

For maximum control (custom framing, performance-critical code), use the Protocol API:

```python
import asyncio

class EchoProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        print('Connection made')

    def data_received(self, data: bytes):
        self.transport.write(data)   # echo back

    def connection_lost(self, exc):
        print('Connection lost')

async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(EchoProtocol, '127.0.0.1', 8000)
    async with server:
        await server.serve_forever()
```

| Callback | Called when… |
|---|---|
| `connection_made(transport)` | A new connection is established |
| `data_received(data)` | Data arrives |
| `eof_received()` | Client closes write side |
| `connection_lost(exc)` | Connection closed (exc is None if normal) |

Streams are built on top of the Protocol API — prefer Streams unless you need low-level framing.

---

## Reading Command-Line Input Asynchronously (Unix only)

`loop.connect_read_pipe` wraps stdin as a stream so you can read from it without blocking:

```python
async def read_stdin():
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    while line := await reader.readline():
        print(f'Input: {line.decode().strip()}')
```

> **Note:** `connect_read_pipe` is Unix-only. Windows requires a thread-based workaround.

---

## Key Takeaway
The Streams API is the right abstraction for most TCP server/client code. `start_server` + `StreamReader`/`StreamWriter` eliminates raw socket boilerplate. Broadcast patterns (fan-out) should create a new task per recipient so a slow or disconnecting client does not block others. Drop down to the Protocol API only for advanced framing or performance requirements.
