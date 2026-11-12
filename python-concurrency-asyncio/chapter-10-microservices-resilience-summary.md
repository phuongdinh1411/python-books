# Chapter 10 – Microservices and Resilience Patterns

## Core Idea
Chapter 10 applies asyncio to a real-world microservice architecture — a Backend-for-Frontend (BFF) that aggregates data from multiple downstream services. It introduces two resilience patterns that are especially important in async systems: **retries with exponential back-off** and the **circuit breaker**.

---

## Backend-for-Frontend (BFF) Pattern

A BFF is an API gateway that composes data from several backend microservices into a single response tailored for one frontend client (mobile, web, etc.).

```
Client → BFF API → [UserService, ProductService, OrderService]
```

Because the BFF makes multiple outbound calls, `asyncio.gather` runs them concurrently:

```python
import asyncio, aiohttp

async def get_user(session, user_id: int) -> dict:
    async with session.get(f'http://user-service/users/{user_id}') as r:
        return await r.json()

async def get_orders(session, user_id: int) -> list:
    async with session.get(f'http://order-service/orders?user={user_id}') as r:
        return await r.json()

async def user_dashboard(user_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        user, orders = await asyncio.gather(
            get_user(session, user_id),
            get_orders(session, user_id)
        )
    return {'user': user, 'orders': orders}
```

---

## Retries with Exponential Back-off

Transient failures (network blips, temporary overload) should be retried. Exponential back-off adds jitter to avoid thundering herds.

```python
import asyncio, aiohttp
from random import uniform

async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    max_retries: int = 3,
    base_delay: float = 0.1
) -> dict:
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + uniform(0, 0.1)  # jitter
            print(f'Attempt {attempt + 1} failed. Retrying in {delay:.2f}s')
            await asyncio.sleep(delay)
```

### Back-off schedule example (base_delay=0.1, max_retries=4):

| Attempt | Delay |
|---|---|
| 1 | 0.1 s + jitter |
| 2 | 0.2 s + jitter |
| 3 | 0.4 s + jitter |
| 4 (final) | raises |

---

## Circuit Breaker Pattern

Retries help with *transient* failures. If a downstream service is completely down, retrying every request wastes resources and degrades the whole system. The circuit breaker opens when failures exceed a threshold, **failing fast** for a cool-down period, then *half-opens* to probe recovery.

### States

```
CLOSED ──(failure threshold hit)──▶ OPEN ──(reset timeout)──▶ HALF-OPEN
   ▲                                                                │
   └──────────────────(probe succeeds)──────────────────────────────┘
```

| State | Behaviour |
|---|---|
| **Closed** | Normal operation; failure count tracked |
| **Open** | All calls fail fast (no network attempt) |
| **Half-open** | One probe call allowed; success → Closed, failure → Open |

### Implementation sketch

```python
import asyncio
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 30.0):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time: datetime | None = None

    async def call(self, coro):
        if self.state == CircuitState.OPEN:
            if datetime.now() > self.last_failure_time + timedelta(seconds=self.reset_timeout):
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception('Circuit is OPEN — failing fast')

        try:
            result = await coro
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### Usage

```python
breaker = CircuitBreaker(failure_threshold=3, reset_timeout=30.0)

async def call_order_service(session, user_id):
    coro = fetch_orders(session, user_id)
    return await breaker.call(coro)
```

---

## Combining Retry + Circuit Breaker

```python
async def resilient_call(session, url):
    try:
        return await fetch_with_retry(session, url, max_retries=2)
    except Exception as e:
        # after retries exhausted, circuit breaker may open
        print(f'Failed after retries: {e}')
        raise
```

**Order matters:** retry *inside* the circuit breaker. A circuit breaker trip should not be triggered by retried failures counted multiple times.

---

## Key Takeaway
In a microservice BFF, use `asyncio.gather` to fan out concurrent downstream calls. Wrap calls in **retry with exponential back-off** for transient failures. Layer a **circuit breaker** on top to fail fast and protect downstream services from overload when there are persistent failures. These patterns are especially impactful with async code because a single async BFF can amplify load onto downstream services very quickly.
