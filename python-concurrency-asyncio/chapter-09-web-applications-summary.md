# Chapter 9 – Web Applications

## Core Idea
Chapter 9 brings asyncio to production web development. It covers three progressive approaches: a hand-built REST API with `aiohttp`, the ASGI specification (asyncio's answer to WSGI), and a real framework (Starlette). It also benchmarks async vs. sync and introduces WebSockets.

---

## Building a REST API with aiohttp

`aiohttp` doubles as an async HTTP *server* (not just a client). It owns its own event loop and does not require an external WSGI server.

```python
from aiohttp import web
import asyncpg

routes = web.RouteTableDef()

@routes.get('/brands')
async def get_brands(request: web.Request) -> web.Response:
    pool = request.app['pool']
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT brand_id, brand_name FROM brand')
    return web.json_response([dict(r) for r in rows])

@routes.post('/product')
async def create_product(request: web.Request) -> web.Response:
    body = await request.json()
    pool = request.app['pool']
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO product (product_name, brand_id) VALUES ($1, $2)',
            body['product_name'], body['brand_id']
        )
    return web.Response(status=201)

async def create_pool(app):
    app['pool'] = await asyncpg.create_pool(...)

app = web.Application()
app.on_startup.append(create_pool)
app.add_routes(routes)
web.run_app(app)
```

---

## aiohttp vs. Flask — Performance Benchmark

Test: 30 seconds, 1 thread, 200 concurrent connections on an 8-core machine.

| Framework | Workers | Requests/sec |
|---|---|---|
| Flask + Gunicorn | 8 | ~551 |
| aiohttp | 1 | ~1,558 |

aiohttp handles **~3× more requests** with a *single process* because async suspension allows it to interleave I/O waits across hundreds of connections simultaneously. Flask with 8 workers handles at most 8 requests concurrently.

---

## ASGI — Asynchronous Server Gateway Interface

WSGI was designed for synchronous code; there is no place to use `await`. ASGI redesigns the API with coroutines:

```python
# WSGI (sync only)
def application(environ, start_response):
    start_response('200 OK', [])
    return [b'Hello']

# ASGI (async-native)
async def application(scope, receive, send):
    await send({'type': 'http.response.start', 'status': 200, 'headers': []})
    await send({'type': 'http.response.body', 'body': b'Hello'})
```

| | WSGI | ASGI |
|---|---|---|
| Standard PEP | PEP 333 (accepted 2004) | Not yet a formal PEP |
| Supports `await` | ❌ | ✅ |
| WebSockets | ❌ | ✅ |
| Example servers | Gunicorn, uWSGI | Uvicorn, Hypercorn |
| Example frameworks | Flask, Django (sync) | Starlette, Django (async), FastAPI |

Run with Uvicorn:
```bash
uvicorn myapp:application
```

---

## Starlette — ASGI Framework

Starlette is a lightweight ASGI framework by Encode (also creators of Uvicorn).

```python
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
import asyncpg

async def brands(request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT brand_id, brand_name FROM brand')
    return JSONResponse([dict(r) for r in rows])

async def on_startup():
    app.state.pool = await asyncpg.create_pool(...)

async def on_shutdown():
    await app.state.pool.close()

app = Starlette(
    routes=[Route('/brands', brands)],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown]
)
```

---

## Django with ASGI

Django 3.1+ supports ASGI. Run with Gunicorn + Uvicorn workers for production:

```bash
gunicorn myproject.asgi:application -w 4 -k uvicorn.workers.UvicornWorker
```

Django async views require `async def`:
```python
from django.http import JsonResponse
import asyncpg

async def brands(request):
    pool = request.app['pool']   # or use Django ORM with sync_to_async
    ...
    return JsonResponse(data)
```

---

## WebSockets

WebSockets provide full-duplex, long-lived connections over HTTP upgrade. ASGI supports them natively.

### With Starlette
```python
from starlette.websockets import WebSocket

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f'Echo: {data}')
    except Exception:
        await websocket.close()
```

Register as a route:
```python
from starlette.routing import WebSocketRoute

app = Starlette(routes=[
    WebSocketRoute('/ws', websocket_endpoint)
])
```

WebSocket connections stay open — perfect for chat, live dashboards, and real-time notifications.

---

## Key Takeaway
Use aiohttp or Starlette for green-field async APIs; use Django + ASGI workers when you need Django's ecosystem. ASGI + Uvicorn is the production stack: coroutines handle hundreds of concurrent connections per worker, WebSockets are first-class, and async DB drivers (asyncpg) keep the loop free. Never mix blocking calls (psycopg2, requests) into async request handlers without offloading to a thread pool.
