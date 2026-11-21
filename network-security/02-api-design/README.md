# Part 2 — API Design

> **Duration:** 2 days | **Priority:** 🔴 Critical
> *"REST / gRPC, clean and well-documented interfaces"* — WorldQuant Senior SWE JD

---

## 🎯 Learning Objectives

- Design REST APIs that are versioned, paginated, idempotent, and documented
- Know when gRPC beats REST and how to use it
- Implement token bucket and sliding window rate limiting
- Design a webhook system with retries and signature verification
- Handle the hardest API problems: pagination at scale, backward compatibility

---

## Section 1 — REST Design

### Resource-Oriented Design

```
REST = Representational State Transfer
Core idea: model your domain as resources (nouns), not actions (verbs)

BAD (RPC-style):
  POST /getUser
  POST /createOrder
  POST /cancelOrder

GOOD (resource-style):
  GET    /users/{id}
  POST   /orders
  DELETE /orders/{id}
  PATCH  /orders/{id}      # partial update
  PUT    /orders/{id}      # full replacement

Resource naming:
  /users              → collection
  /users/{id}         → single resource
  /users/{id}/orders  → sub-collection (orders belonging to a user)
  /orders?user_id=42  → filtering via query params (alternative to nesting)

Avoid deep nesting (> 2 levels):
  BAD:  /users/{uid}/orders/{oid}/items/{iid}/comments
  GOOD: /comments?item_id={iid}
```

### Status Codes — Use Them Correctly

```
2xx Success:
  200 OK           → GET, PUT, PATCH success
  201 Created      → POST success (include Location: /resource/{id} header)
  202 Accepted     → async operation started (return job_id)
  204 No Content   → DELETE success (no body)

3xx Redirect:
  301 Moved Permanently → resource has a new permanent URL
  304 Not Modified      → client cache is still valid (ETag / Last-Modified)

4xx Client Error:
  400 Bad Request   → malformed request, validation failure
  401 Unauthorized  → not authenticated (send/renew credentials)
  403 Forbidden     → authenticated but not allowed (permissions)
  404 Not Found     → resource doesn't exist
  409 Conflict      → state conflict (duplicate, optimistic lock failure)
  410 Gone          → permanently deleted (don't retry)
  422 Unprocessable → syntactically valid but semantically wrong
  429 Too Many Requests → rate limited (include Retry-After header)

5xx Server Error:
  500 Internal Server Error → bug or unexpected failure
  502 Bad Gateway           → upstream service returned invalid response
  503 Service Unavailable   → overloaded or in maintenance (include Retry-After)
  504 Gateway Timeout       → upstream service timed out

Interview traps:
  401 vs 403: 401 = "who are you?", 403 = "I know who you are, still no"
  404 vs 410: 410 = never try again (permanent), 404 = may come back
  400 vs 422: 422 is more specific to semantic validation failures
```

### Request/Response Design

```python
# GOOD: consistent, predictable API response format

# Success (single resource)
{
    "data": {
        "id": "ord_abc123",
        "status": "completed",
        "total": 150.00,
        "created_at": "2024-01-15T09:30:00Z"  # always UTC ISO 8601
    }
}

# Success (collection with pagination)
{
    "data": [...],
    "meta": {
        "total": 1500,
        "page": 2,
        "per_page": 50,
        "has_next": true,
        "next_cursor": "eyJpZCI6MTAwfQ=="  # base64 cursor
    }
}

# Error (always include machine-readable code)
{
    "error": {
        "code": "VALIDATION_ERROR",          # machine-readable
        "message": "title is required",       # human-readable
        "details": [                          # field-level errors
            {"field": "title", "message": "must not be empty"},
            {"field": "priority", "message": "must be between 1 and 5"}
        ],
        "request_id": "req_7f9b2c3d"         # for debugging
    }
}
```

---

## Section 2 — API Versioning

### Why Versioning Is Hard

```
Backward-compatible changes (safe, no version bump needed):
  ✅ Add a new optional field to responses
  ✅ Add a new optional query parameter
  ✅ Add a new endpoint
  ✅ Relax validation (accept previously-rejected input)

Breaking changes (require version bump):
  ❌ Remove or rename a field
  ❌ Change a field's type (string → integer)
  ❌ Make a previously-optional field required
  ❌ Change behavior of an existing endpoint
  ❌ Remove an endpoint
```

### Versioning Strategies

```
Strategy 1: URL path versioning (most common, recommended)
  GET /v1/orders/{id}
  GET /v2/orders/{id}
  Pros: visible, cacheable, easy to test, easy to route in API gateway
  Cons: clients must update URL when migrating

Strategy 2: Header versioning
  GET /orders/{id}
  Accept: application/vnd.example.v2+json
  Pros: clean URLs
  Cons: not visible in browser, harder to cache, annoying to test

Strategy 3: Query param versioning
  GET /orders/{id}?version=2
  Pros: easy to test in browser
  Cons: pollutes query params, caching issues

Recommendation: use URL versioning (/v1/, /v2/)
                run v1 and v2 simultaneously during migration
                deprecate v1 with a sunset header: Sunset: Sat, 31 Dec 2024 23:59:59 GMT

API Gateway routing:
  /v1/* → v1-service:8080
  /v2/* → v2-service:8080
  Can run simultaneously, migrate clients gradually
```

---

## Section 3 — Pagination at Scale

### Offset Pagination (Simple but Broken at Scale)

```python
# GET /orders?page=5&per_page=50

SELECT * FROM orders
ORDER BY created_at DESC
LIMIT 50 OFFSET 200;  -- skip 200 rows, take next 50

# Problems:
# 1. OFFSET 200 still reads and discards 200 rows from disk — O(offset) cost
#    At page 10,000 with 50 items: OFFSET 500,000 → reads 500K rows, throws most away
# 2. Page drift: if a new item is inserted while user is paginating,
#    page N+1 may repeat items from page N (or skip items)
# 3. Useless for real-time data (positions shift constantly)

# When it's OK: small datasets (< 10K total rows), admin UIs, no real-time updates
```

### Cursor Pagination (Correct, Scalable)

```python
# GET /orders → returns next_cursor
# GET /orders?cursor=eyJpZCI6MTAwfQ== → next page

# Server-side:
import base64
import json

def encode_cursor(last_id: int, last_ts: str) -> str:
    return base64.b64encode(
        json.dumps({"id": last_id, "ts": last_ts}).encode()
    ).decode()

def decode_cursor(cursor: str) -> dict:
    return json.loads(base64.b64decode(cursor.encode()).decode())

# Query using cursor (no OFFSET!):
async def get_orders(cursor: str | None, limit: int = 50) -> dict:
    if cursor:
        pos = decode_cursor(cursor)
        # Use composite key to handle ties on created_at
        rows = await db.fetch("""
            SELECT * FROM orders
            WHERE (created_at, id) < (%(ts)s::timestamptz, %(id)s)
            ORDER BY created_at DESC, id DESC
            LIMIT %(limit)s
        """, {"ts": pos["ts"], "id": pos["id"], "limit": limit + 1})
    else:
        rows = await db.fetch("""
            SELECT * FROM orders
            ORDER BY created_at DESC, id DESC
            LIMIT %(limit)s
        """, {"limit": limit + 1})

    has_next = len(rows) > limit
    items = rows[:limit]
    next_cursor = None
    if has_next:
        last = items[-1]
        next_cursor = encode_cursor(last["id"], last["created_at"].isoformat())

    return {"data": items, "meta": {"next_cursor": next_cursor, "has_next": has_next}}

# Advantages:
# - O(1) query cost regardless of page (uses index seek, not offset)
# - Stable: new items don't shift existing pages
# - Works with real-time data

# Disadvantages:
# - No "jump to page N" (sequential only)
# - Cursor is opaque (users can't construct it)
```

### Keyset Pagination (Best for Financial Data)

```sql
-- For financial time-series: paginate by (instrument_id, date)
-- GET /prices?after_symbol=AAPL&after_date=2024-01-15

SELECT *
FROM prices
WHERE (symbol, valid_date) > ('AAPL', '2024-01-15')  -- keyset
ORDER BY symbol ASC, valid_date ASC
LIMIT 100;

-- Uses composite index on (symbol, valid_date) → O(log N) seek, then sequential scan
-- Perfect for: ordered financial data, time-series exports
```

---

## Section 4 — Rate Limiting

### Token Bucket Algorithm

```python
import time
from threading import Lock
from dataclasses import dataclass

@dataclass
class TokenBucket:
    """
    Tokens refill at `rate` per second up to `capacity`.
    Each request consumes `cost` tokens.
    If not enough tokens: reject (or wait).

    Burst: if no requests for 10s, bucket fills to capacity → allows burst
    """
    rate: float      # tokens per second
    capacity: float  # max tokens (burst limit)

    def __post_init__(self):
        self._tokens = self.capacity
        self._last_refill = time.monotonic()
        self._lock = Lock()

    def consume(self, cost: float = 1.0) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self.capacity,
                self._tokens + elapsed * self.rate
            )
            self._last_refill = now

            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False

    def wait_time(self) -> float:
        """How long to wait before next token is available."""
        with self._lock:
            if self._tokens >= 1:
                return 0.0
            return (1 - self._tokens) / self.rate


# Redis-backed distributed token bucket (across multiple API servers)
import redis.asyncio as aioredis

BUCKET_SCRIPT = """
local key      = KEYS[1]
local rate     = tonumber(ARGV[1])   -- tokens per second
local capacity = tonumber(ARGV[2])   -- max tokens
local now      = tonumber(ARGV[3])   -- current unix timestamp (float)
local cost     = tonumber(ARGV[4])   -- tokens this request costs

local data     = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens   = tonumber(data[1]) or capacity
local last     = tonumber(data[2]) or now

-- Refill
local elapsed = math.max(0, now - last)
tokens = math.min(capacity, tokens + elapsed * rate)

-- Consume
if tokens >= cost then
    tokens = tokens - cost
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return 1   -- allowed
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return 0   -- rejected
end
"""

async def is_allowed(redis: aioredis.Redis, user_id: str,
                     rate: float = 10, capacity: float = 100) -> bool:
    key = f"ratelimit:{user_id}"
    result = await redis.eval(
        BUCKET_SCRIPT, 1, key,
        rate, capacity, time.time(), 1
    )
    return bool(result)
```

### Sliding Window (No Burst, More Precise)

```python
# Sliding window using Redis sorted set (score = timestamp)
async def sliding_window_check(
    redis: aioredis.Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> bool:
    now = time.time()
    window_start = now - window_seconds
    request_id = f"{now}-{random.random()}"

    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, window_start)   # remove old entries
        pipe.zadd(key, {request_id: now})             # add this request
        pipe.zcard(key)                               # count in window
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()

    count = results[2]
    return count <= limit

# Leaky bucket: constant output rate, excess queued or dropped
# Difference from token bucket: no burst — requests are smoothed
```

### FastAPI Rate Limit Middleware

```python
from fastapi import FastAPI, Request, HTTPException, status
import redis.asyncio as aioredis

app = FastAPI()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Identify client (IP, API key, or user_id)
    api_key = request.headers.get("X-API-Key", "anonymous")
    key = f"ratelimit:{api_key}"

    allowed = await is_allowed(request.app.state.redis, key, rate=10, capacity=100)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": "1",
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 1),
            }
        )
    return await call_next(request)
```

---

## Section 5 — REST vs gRPC

### When gRPC Wins

```
gRPC advantages:
  ✅ Protobuf: 5–7x smaller payload than JSON, faster to serialize
  ✅ Strongly typed: schema is the contract — breaking changes caught at compile time
  ✅ Streaming: unary, server-streaming, client-streaming, bidirectional
  ✅ HTTP/2 multiplexing: many RPCs over one connection
  ✅ Code generation: clients in 10+ languages from one .proto file

gRPC disadvantages:
  ❌ Not human-readable (binary) — harder to debug with curl/browser
  ❌ Requires HTTP/2 (harder to use with some load balancers, proxies)
  ❌ Steeper learning curve than REST

Choose gRPC for:
  - Internal microservice-to-microservice communication
  - High-throughput services where JSON overhead matters
  - Streaming data (real-time price feeds, log streaming)
  - Polyglot systems (many languages need the same API)

Choose REST for:
  - Public APIs (browser, mobile, 3rd party)
  - Simple CRUD where HTTP semantics are a good fit
  - When debuggability and human readability matter
  - Teams unfamiliar with protobuf
```

### gRPC in Python

```python
# 1. Define the contract in a .proto file
# signals.proto
syntax = "proto3";

service SignalService {
    rpc GetSignal(SignalRequest) returns (SignalResponse);
    rpc StreamPrices(PriceStreamRequest) returns (stream PriceUpdate);
    rpc BatchCompute(stream SignalRequest) returns (stream SignalResponse);
}

message SignalRequest {
    string symbol = 1;
    string from_date = 2;
    string to_date = 3;
}

message SignalResponse {
    string symbol = 1;
    repeated double values = 2;
    string computed_at = 3;
}

# 2. Generate Python code
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. signals.proto

# 3. Server implementation
import grpc
import signals_pb2
import signals_pb2_grpc
from concurrent import futures

class SignalServicer(signals_pb2_grpc.SignalServiceServicer):
    async def GetSignal(self, request, context):
        values = await compute_signal(request.symbol, request.from_date, request.to_date)
        return signals_pb2.SignalResponse(
            symbol=request.symbol,
            values=values,
            computed_at=datetime.utcnow().isoformat(),
        )

    async def StreamPrices(self, request, context):
        """Server-side streaming: send prices as they arrive."""
        async for price in subscribe_to_prices(request.symbol):
            yield signals_pb2.PriceUpdate(symbol=request.symbol, price=price)
            if context.cancelled():  # client disconnected
                break

server = grpc.aio.server()
signals_pb2_grpc.add_SignalServiceServicer_to_server(SignalServicer(), server)
server.add_insecure_port("[::]:50051")
await server.start()

# 4. Client
async with grpc.aio.insecure_channel("localhost:50051") as channel:
    stub = signals_pb2_grpc.SignalServiceStub(channel)
    response = await stub.GetSignal(signals_pb2.SignalRequest(
        symbol="AAPL", from_date="2024-01-01", to_date="2024-12-31"
    ))
    print(response.values[:5])

# Streaming client
async for update in stub.StreamPrices(signals_pb2.PriceStreamRequest(symbol="AAPL")):
    print(update.price)
```

---

## Section 6 — Webhooks

### Design a Webhook System

```
Problem: your service needs to notify external clients when events happen
         (order completed, signal computed, job finished)
         Push model: you call them, not they call you

Components:
  1. Webhook registration: client registers URL + events they want
  2. Event publishing: your service fires events internally
  3. Webhook dispatcher: picks up events, calls client URLs
  4. Retry + dead-letter: handles delivery failures
  5. Signature verification: proves the webhook came from you
```

```python
# Webhook dispatcher with retries + signature

import hmac
import hashlib
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class WebhookDispatcher:

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=1, max=60),
    )
    async def dispatch(self, webhook: Webhook, event: dict) -> None:
        """Deliver event to webhook URL with HMAC signature."""
        payload = json.dumps(event, sort_keys=True).encode()
        timestamp = str(int(time.time()))

        # HMAC-SHA256 signature (like Stripe/GitHub webhooks)
        # Prevents attackers from forging fake webhooks to your clients
        signature = hmac.new(
            webhook.secret.encode(),
            f"{timestamp}.{payload.decode()}".encode(),
            hashlib.sha256,
        ).hexdigest()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": f"sha256={signature}",
                    "X-Webhook-Timestamp": timestamp,
                    "X-Webhook-Event": event["type"],
                    "X-Delivery-ID": str(uuid.uuid4()),
                },
            )
            response.raise_for_status()   # retry on 5xx

# Client-side signature verification (how your users verify your webhooks)
def verify_webhook(payload: bytes, signature: str, timestamp: str, secret: str) -> bool:
    # Reject stale webhooks (> 5 min old) to prevent replay attacks
    if abs(time.time() - int(timestamp)) > 300:
        return False
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.{payload.decode()}".encode(),
        hashlib.sha256,
    ).hexdigest()
    # Use hmac.compare_digest (constant time) to prevent timing attacks
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## Section 7 — API Gateway

```
Responsibilities of an API Gateway:
  ✅ Routing: /v1/* → service-v1, /v2/* → service-v2
  ✅ Auth: validate JWT before forwarding to services
  ✅ Rate limiting: enforce per-client limits at the edge
  ✅ Request/response transformation: strip internal headers, add correlation IDs
  ✅ SSL termination: handle TLS so internal services don't need to
  ✅ Load balancing: distribute across service instances
  ✅ Observability: log every request, emit latency metrics

What NOT to put in an API Gateway:
  ❌ Business logic (belongs in services)
  ❌ Heavy computation (gateway should be thin and fast)
  ❌ Database queries (stateless — it's a router, not a service)

Tools: Kong, AWS API Gateway, nginx, Envoy, Traefik

Interview question: "What's the difference between an API gateway and a reverse proxy?"
  → Both route traffic, but API gateway adds: auth, rate limiting, request transformation
  → nginx is a reverse proxy; Kong (built on nginx) is an API gateway
```

---

## 🏋️ Exercises

### Exercise 1 — Design a Financial Signals API
Design a REST API for serving computed alpha signals:
- Versioning strategy (v1 → v2 migration)
- Pagination (cursor-based, millions of records)
- Rate limiting (different tiers: researcher vs algo trader)
- Error response format

### Exercise 2 — Implement Token Bucket Rate Limiter
Implement in Python + Redis (use the Lua script from Section 4).
Test: 100 requests/sec, bucket allows 10/sec with burst of 20.
Verify: first 20 requests pass (burst), next 80 are rate-limited.

### Exercise 3 — gRPC vs REST Decision
For each service pair, decide: REST or gRPC, and explain why:
1. Public API for external hedge fund partners consuming signals
2. Internal service: order management → risk calculation (high freq)
3. ML model serving: Python service → real-time scoring endpoint
4. Admin dashboard → user management service

---

## ✅ Self-Check Questions

1. What is idempotency? Which HTTP methods are idempotent?
2. What is the difference between 401 and 403?
3. Why is offset pagination broken at scale? What's the alternative?
4. How does a token bucket differ from a leaky bucket?
5. What does `Retry-After` header communicate to clients?
6. When would you choose gRPC over REST?
7. What is the purpose of an HMAC signature on a webhook?
8. What breaks backward compatibility in a REST API?
9. What is cursor-based pagination and why is it O(1)?
10. What should and should NOT go into an API gateway?

---

## 🔗 Key Links

- https://www.iana.org/assignments/http-status-codes/ — HTTP status codes
- https://grpc.io/docs/languages/python/basics/ — gRPC Python guide
- https://stripe.com/docs/webhooks — Stripe webhook reference (gold standard design)
- https://swagger.io/specification/ — OpenAPI specification
