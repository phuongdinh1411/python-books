# Chapter 12 – Asynchronous Queues

## Core Idea
`asyncio.Queue` decouples producers (tasks that generate work) from consumers (tasks that process work). It also provides natural backpressure through a `maxsize` bound. Chapter 12 applies queues to two practical patterns: background task processing in a web application, and a publish–subscribe (pub/sub) broadcast system.

---

## `asyncio.Queue` Basics

```python
import asyncio

queue = asyncio.Queue(maxsize=10)   # bounded: blocks producers when full

await queue.put(item)       # waits if queue is full (backpressure)
queue.put_nowait(item)      # raises QueueFull immediately if full
item = await queue.get()    # waits if queue is empty
queue.task_done()           # signal that a consumed item is processed
await queue.join()          # blocks until every item has been task_done'd
```

### Poison pill pattern (stop workers)
```python
# Put one None per worker to signal shutdown
for _ in workers:
    await queue.put(None)
```

---

## Producer–Consumer Example (Supermarket Checkout)

```python
import asyncio
from asyncio import Queue
from dataclasses import dataclass, field
from random import randrange

@dataclass
class Product:
    name: str
    checkout_time: float

@dataclass
class Customer:
    customer_id: int
    products: list[Product] = field(default_factory=list)

async def checkout_customer(queue: Queue, cashier_id: int):
    while True:
        customer = await queue.get()
        for product in customer.products:
            await asyncio.sleep(product.checkout_time)
        queue.task_done()

async def customer_generator(queue: Queue):
    customer_id = 0
    while True:
        new_customers = [Customer(customer_id + i) for i in range(randrange(5))]
        for c in new_customers:
            await queue.put(c)   # blocks if queue full — backpressure
        customer_id += len(new_customers)
        await asyncio.sleep(1)

async def main():
    queue = Queue(maxsize=5)   # max 5 waiting customers
    producer = asyncio.create_task(customer_generator(queue))
    cashiers = [asyncio.create_task(checkout_customer(queue, i)) for i in range(3)]
    await asyncio.gather(producer, *cashiers)

asyncio.run(main())
```

---

## Queues in Web Applications

**Problem:** an order endpoint calls a slow external order management system. The user must not wait for the slow call.

**Solution:** put the order on a queue and return 200 immediately. Background workers process it.

```python
from aiohttp import web
from asyncio import Queue
import asyncio

routes = web.RouteTableDef()

async def order_worker(worker_id: int, queue: Queue):
    while True:
        order = await queue.get()
        await asyncio.sleep(order)   # simulate slow order processing
        print(f'Worker {worker_id}: processed order {order}')
        queue.task_done()

@routes.post('/order')
async def place_order(request: web.Request) -> web.Response:
    queue: Queue = request.app['order_queue']
    await queue.put(randrange(5))   # non-blocking from user's perspective
    return web.Response(text='Order placed!')

async def on_startup(app):
    queue = Queue(maxsize=10)
    app['order_queue'] = queue
    app['workers'] = [
        asyncio.create_task(order_worker(i, queue)) for i in range(3)
    ]

async def on_shutdown(app):
    # Wait for in-flight orders before shutting down
    await app['order_queue'].join()
    for worker in app['workers']:
        worker.cancel()

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
app.add_routes(routes)
web.run_app(app)
```

This pattern provides:
- **Instant user response** — the endpoint returns immediately.
- **Bounded concurrency** — `maxsize` limits queue depth; bounded workers limit concurrent calls to the slow service.
- **Graceful shutdown** — `queue.join()` ensures all pending orders complete before exit.

---

## Pub/Sub with Queues

Fan a single message stream to multiple subscribers, each with their own queue:

```python
import asyncio
from asyncio import Queue
from typing import Callable

class PubSub:
    def __init__(self):
        self._subscribers: list[Queue] = []

    def subscribe(self) -> Queue:
        q: Queue = Queue()
        self._subscribers.append(q)
        return q

    async def publish(self, message):
        for q in self._subscribers:
            await q.put(message)

async def subscriber(name: str, queue: Queue):
    while True:
        msg = await queue.get()
        print(f'{name} received: {msg}')

async def main():
    pubsub = PubSub()
    q1 = pubsub.subscribe()
    q2 = pubsub.subscribe()

    consumers = [
        asyncio.create_task(subscriber('Alice', q1)),
        asyncio.create_task(subscriber('Bob', q2)),
    ]

    for i in range(5):
        await pubsub.publish(f'message-{i}')
        await asyncio.sleep(0.5)
```

---

## Queue Variants

| Class | Ordering |
|---|---|
| `asyncio.Queue` | FIFO |
| `asyncio.LifoQueue` | LIFO (stack) |
| `asyncio.PriorityQueue` | Smallest item first |

```python
pq = asyncio.PriorityQueue()
await pq.put((1, 'low priority'))
await pq.put((0, 'high priority'))   # lower number = higher priority
item = await pq.get()               # (0, 'high priority')
```

---

## Key Takeaway
`asyncio.Queue` is the right tool when producers and consumers run at different speeds. A bounded queue provides natural backpressure — producers slow down when consumers can't keep up, preventing memory growth. Use `queue.join()` in shutdown hooks to drain in-flight work cleanly. The pub/sub variant scales a single producer to many independent consumers.
