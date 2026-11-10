# Chapter 4 – Asyncio Libraries and Case Studies

## Core Idea
This chapter demonstrates asyncio applied to real-world use cases through progressively complex case studies. It covers the standard library Streams API, then third-party libraries: Twisted, Janus, aiohttp, ZeroMQ, asyncpg, and Sanic.

---

## Streams (Standard Library) — The High-Level Networking API

The Streams API is the easiest way to write network applications with asyncio:
- `asyncio.open_connection(host, port)` → `(StreamReader, StreamWriter)` for clients
- `asyncio.start_server(handler, host, port)` → TCP server that calls `handler(reader, writer)` per connection

```python
import asyncio

async def echo(reader, writer):
    try:
        while data := await reader.readline():
            writer.write(data.upper())
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(echo, '127.0.0.1', 8888)
    async with server:
        await server.serve_forever()

asyncio.run(main())
```

### Case Study: Message Queue (v1 — Naive)
- Built a toy pub-sub message broker in ~40 lines
- Clients first send a channel name to subscribe to, then send `(channel, data)` pairs
- `/queue` channels use round-robin (point-to-point); `/topic` channels broadcast to all
- **Problem:** `await gather(*[send_msg(c, data) for c in conns])` blocks the entire receive loop until the slowest subscriber is done

### Case Study: Message Queue (v2 — Improved)
**Solution:** Decouple receiving and sending with per-client and per-channel queues:
- Each client gets its own `asyncio.Queue` + a dedicated `send_client()` coroutine
- Each channel gets its own `asyncio.Queue` + a `chan_sender()` coroutine
- Result: a slow subscriber only affects itself — other subscribers are unblocked
- **Key design pattern:** Use bounded `asyncio.Queue(maxsize=...)` instances to decouple producers and consumers. Choose a policy for full queues (wait, drop, or disconnect); unbounded buffering only turns a slow consumer into growing RAM usage.

---

## Twisted

- Pre-dates asyncio by ~14 years; heavily influenced asyncio's design
- Has battle-tested implementations of HTTP, XMPP, NNTP, IMAP, SSH, IRC, FTP, DNS, SMTP, etc.
- Since Python 3.5, Twisted supports running on the asyncio event loop (`asyncioreactor.install()`)
- You can now use `async def` and `await` directly in Twisted code:
```python
from twisted.internet import asyncioreactor
asyncioreactor.install()  # must come before importing reactor!
```
- Asyncio ≠ replacement for Twisted — their rich protocol libraries are still valuable

---

## Janus Queue — Bridging Threads and Coroutines

The standard library has `queue.Queue` (blocking, for threads) and `asyncio.Queue` (async, for coroutines) — but **neither works across the boundary**.

`janus.Queue` provides both APIs from a single object:

```python
queue = janus.Queue()

# In a thread:
queue.sync_q.put(data)       # blocking

# In a coroutine:
data = await queue.async_q.get()  # async
```

Use when you have long-running blocking code in threads that needs to stream data to coroutines.

---

## aiohttp — HTTP Client + Server

`aiohttp` is the go-to library for async HTTP:

### As a server:
```python
from aiohttp import web

async def hello(request):
    return web.Response(text="Hello, world")

app = web.Application()
app.router.add_get('/', hello)
web.run_app(app, port=8080)
```

### As a client:
```python
async with ClientSession() as session:
    async with session.get(url) as resp:
        data = await resp.read()
```

### Case Study: News Scraper
- `aiohttp` server receives `/news` requests
- Server concurrently fetches CNN and Al Jazeera pages via Splash (JS rendering service in Docker)
- Uses `asyncio.create_task()` + `asyncio.gather()` to fetch both sites in parallel
- Scrapes headlines with BeautifulSoup, merges and returns as an HTML page
- **Key takeaway:** `aiohttp` hides event loop machinery behind a clean API

---

## ØMQ (ZeroMQ) — Smart Sockets

ZeroMQ provides "smart" sockets that handle:
- **Message framing** — no need to count bytes or design a wire protocol
- **Auto-reconnection** — if server restarts, clients reconnect automatically
- **Buffering** — messages sent during disconnection are queued and delivered on reconnect

Socket types: `PUSH/PULL` (one-directional), `PUB/SUB` (broadcast), `REQ/REP` (request-reply), etc.

### Case Study: Multiple Sockets
- Traditional approach: `zmq.Poller` to multiplex multiple sockets — awkward code
- Asyncio approach: one coroutine per socket — each with its own clean `async for` loop:
```python
async def do_receiver():
    sock = context.socket(zmq.PULL)
    sock.connect("tcp://localhost:5557")
    while message := await sock.recv_json():
        print(f'Via PULL: {message}')
```

### Case Study: Application Performance Monitoring
- Microservices emit CPU/memory metrics via ØMQ `PUB` socket every second
- A central `metric-server.py` collects via `SUB` socket, serves an aiohttp web app
- Browser connects via **Server-Sent Events (SSE)** and receives live chart updates
- ØMQ + asyncio: when any service restarts, reconnection is **automatic** — zero reconnect code needed

---

## asyncpg — High-Performance PostgreSQL Client

- Written by Yury Selivanov (core asyncio developer)
- Works directly with the PostgreSQL binary protocol; benchmark it against other clients for your workload
- Supports prepared statements, cursors, connection pooling

```python
async with asyncpg.create_pool(dsn) as pool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM users WHERE name=$1', 'Bob')
        await conn.execute('INSERT INTO users(name) VALUES($1)', 'Alice')
```

### Case Study: Cache Invalidation with PostgreSQL LISTEN/NOTIFY
- PostgreSQL can act as an event bus: `NOTIFY channel 'data'` sends an event to all `LISTEN`-ers
- Strategy: when app writes to DB, DB notifies all app instances → each instance updates its cache
- asyncpg supports `conn.add_listener(channel, callback)` for receiving these notifications
- **Key insight:** LISTEN/NOTIFY is a lightweight notification mechanism, not a durable queue. Disconnected listeners miss events; design cache expiry or resynchronization for reconnects.

---

## Sanic — Async Web Framework

- Asyncio-native web framework (similar to Flask API but built for coroutines)
- Provides lifecycle hooks (`@app.listener('before_server_start')`, `@app.listener('after_server_stop')`) for startup/shutdown resource management
- Good for building async REST APIs; simpler than aiohttp for web-only use cases

---

## Key Takeaways
- **Streams API** is the simplest starting point for async socket programming
- Decouple sending and receiving with **`asyncio.Queue`** to prevent slow consumers from blocking producers
- **Janus queue** bridges threads and coroutines when you must mix them
- **aiohttp** is the standard choice for async HTTP client and server work
- **ØMQ** makes multi-socket async code clean — one coroutine per socket, no polling
- **asyncpg** provides async PostgreSQL access; `LISTEN/NOTIFY` can support cache invalidation when missed notifications are handled
- Third-party async libraries abstract away the raw event loop, letting you focus on application logic
