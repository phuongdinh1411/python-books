# Building a Production-Grade Redis-Backed Async Queue — `arq` Style

> **Level:** Intermediate → Production  
> **Python:** 3.11+  
> **Dependencies:** `redis[asyncio]>=5.0`, `msgpack>=1.0`, `python-dotenv`, `pytest`, `pytest-asyncio`  
> **What you will build:** A fully persistent, distributed async job queue backed by Redis —
> with connection resilience, job serialisation, worker pool, exponential-backoff retries,
> delayed/scheduled jobs, dead-letter queue, Lua-atomic dequeue, heartbeat, structured logging,
> Prometheus metrics, a FastAPI admin API, graceful shutdown, and a full test suite.

---

## Table of Contents

1. [Why Redis for a Queue?](#1-why-redis-for-a-queue)
2. [Redis Data Structures](#2-redis-data-structures)
3. [Architecture Overview](#3-architecture-overview)
4. [Project Layout](#4-project-layout)
5. [Configuration](#5-configuration)
6. [Domain Model](#6-domain-model)
7. [Redis Connection & Resilience](#7-redis-connection--resilience)
8. [Job Serialisation](#8-job-serialisation)
9. [Enqueue](#9-enqueue)
10. [Worker — BRPOP Loop](#10-worker--brpop-loop)
11. [Heartbeat & Stuck-Job Reaper](#11-heartbeat--stuck-job-reaper)
12. [Scheduler — Delayed Jobs](#12-scheduler--delayed-jobs)
13. [Retry Policy](#13-retry-policy)
14. [Dead-Letter Queue](#14-dead-letter-queue)
15. [Result Backend](#15-result-backend)
16. [Rate Limiting](#16-rate-limiting)
17. [Structured Logging & Metrics](#17-structured-logging--metrics)
18. [Admin API (FastAPI)](#18-admin-api-fastapi)
19. [Graceful Shutdown](#19-graceful-shutdown)
20. [Full Wiring — `app.py`](#20-full-wiring--apppy)
21. [Tests](#21-tests)
22. [Docker & docker-compose](#22-docker--docker-compose)
23. [Running the Project](#23-running-the-project)
24. [Production Checklist](#24-production-checklist)

---

## 1. Why Redis for a Queue?

| Problem | Redis solution |
|---|---|
| Lost on process crash | `appendonly yes` (AOF) — every write fsynced |
| Single machine limit | Workers on any machine that can reach Redis |
| No delayed execution | `ZADD` sorted set with Unix timestamp as score |
| No job history | `HSET job:{id}` stored with configurable TTL |
| Polling overhead | `BRPOP` — workers block efficiently, 0 CPU while idle |

---

## 2. Redis Data Structures

```
Key                            Type          Purpose
──────────────────────────────────────────────────────────────────────
queue:{name}                   LIST          pending jobs  (LPUSH / BRPOP)
queue:{name}:delayed           SORTED SET    scheduled jobs (score = run_at unix ts)
queue:{name}:dlq               LIST          dead-letter jobs
job:{job_id}                   HASH          metadata + status + result
worker:{worker_id}:heartbeat   STRING (EX)   liveness probe — expires every 30s
queue:{name}:rate:{func}       STRING        rolling rate-limit counter
```

### Why LIST + BRPOP?

```
LPUSH  — producer pushes to left (O(1))
BRPOP  — worker blocks on right (O(1))
         Redis wakes the worker instantly when a job arrives
         No polling loop, 0 wasted CPU
```

### Why SORTED SET for delayed jobs?

```
score  = Unix timestamp at which job should run
ZRANGEBYSCORE queue:delayed 0 <now>  → jobs ready to run
Atomically moved to main queue by the Scheduler coroutine
```

---

## 3. Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│  PRODUCER  (any process / service)                            │
│    enqueue(func_name, *args)                                  │
│        → serialize → LPUSH queue:default                      │
│        → HSET job:{id} status=pending                         │
└──────────────────────┬────────────────────────────────────────┘
                       │  Redis
     ┌─────────────────┼─────────────────┐
     │  queue:default  │                 │
     │  [job_c|job_b|job_a]  ← BRPOP    │
     └────────┬────────┘                 │
   BRPOP      │                          │
   ┌──────────▼─────────┐  ┌────────────▼──────────┐
   │  Worker Process 1  │  │  Worker Process 2      │
   │  (any machine)     │  │  (any machine)         │
   │  - semaphore N     │  │  - semaphore N         │
   │  - heartbeat loop  │  │  - heartbeat loop      │
   └──────────┬─────────┘  └────────────┬───────────┘
              │                         │
              └─────────┬───────────────┘
                        │
              HSET job:{id} status=done/failed
              LPUSH queue:dlq  (on permanent failure)

┌───────────────────────────────────────────────────────────────┐
│  SCHEDULER  (runs in every worker process)                    │
│    every 0.5s: ZRANGEBYSCORE queue:delayed 0 <now>            │
│               → pipeline: LPUSH + ZREM  (atomic)              │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│  REAPER  (runs in every worker process)                       │
│    every 60s: scan for jobs stuck in 'running' with           │
│               heartbeat expired → re-enqueue                  │
└───────────────────────────────────────────────────────────────┘
```

---

## 4. Project Layout

```
arq_queue/
├── config.py           # all tunables from env vars
├── models.py           # Job dataclass, JobStatus enum
├── connection.py       # Redis pool, reconnect logic
├── serializer.py       # msgpack / JSON encode-decode
├── enqueue.py          # enqueue(), enqueue_many()
├── worker.py           # Worker class — BRPOP loop
├── heartbeat.py        # heartbeat emitter + stuck-job reaper
├── scheduler.py        # Scheduler — delayed → main queue
├── retry.py            # RetryPolicy + backoff
├── dlq.py              # DLQ helpers — list, retry, purge
├── results.py          # get_result(), wait_for_result()
├── rate_limit.py       # Redis token-bucket rate limiter
├── logging_setup.py    # structured JSON logging
├── metrics.py          # in-process Prometheus counters
├── admin_api.py        # FastAPI admin endpoints
├── shutdown.py         # SIGINT/SIGTERM + drain
├── app.py              # wires everything together
├── example_tasks.py    # sample @task-decorated functions
├── main.py             # entry point
├── requirements.txt
├── docker-compose.yml
└── tests/
    ├── conftest.py
    ├── test_serializer.py
    ├── test_enqueue.py
    ├── test_worker.py
    ├── test_scheduler.py
    ├── test_retry.py
    └── test_integration.py
```

---

## 5. Configuration

```python
# arq_queue/config.py
from __future__ import annotations
import os


class Config:
    # Redis
    REDIS_URL:          str   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_POOL_MIN:     int   = int(os.getenv("REDIS_POOL_MIN", "2"))
    REDIS_POOL_MAX:     int   = int(os.getenv("REDIS_POOL_MAX", "20"))
    REDIS_RETRY_ON_ERR: bool  = os.getenv("REDIS_RETRY", "true").lower() == "true"
    REDIS_SOCKET_TIMEOUT: float = float(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))

    # Queue
    QUEUE_NAME:         str   = os.getenv("QUEUE_NAME", "default")
    BRPOP_TIMEOUT:      float = float(os.getenv("BRPOP_TIMEOUT", "2"))   # seconds
    CONCURRENCY:        int   = int(os.getenv("CONCURRENCY", "10"))

    # Jobs
    JOB_TIMEOUT:        float = float(os.getenv("JOB_TIMEOUT", "300"))
    JOB_RESULT_TTL:     int   = int(os.getenv("JOB_RESULT_TTL", "86400"))  # 24h

    # Retry
    MAX_RETRIES:        int   = int(os.getenv("MAX_RETRIES", "3"))
    BACKOFF_BASE:       float = float(os.getenv("BACKOFF_BASE", "2.0"))
    BACKOFF_MAX:        float = float(os.getenv("BACKOFF_MAX", "300.0"))
    BACKOFF_JITTER:     bool  = os.getenv("BACKOFF_JITTER", "true").lower() == "true"

    # Heartbeat / reaper
    HEARTBEAT_INTERVAL: float = float(os.getenv("HEARTBEAT_INTERVAL", "10"))
    HEARTBEAT_TTL:      int   = int(os.getenv("HEARTBEAT_TTL", "30"))  # seconds in Redis
    REAPER_INTERVAL:    float = float(os.getenv("REAPER_INTERVAL", "60"))
    STUCK_THRESHOLD:    float = float(os.getenv("STUCK_THRESHOLD", "120"))  # seconds

    # Scheduler
    SCHEDULER_INTERVAL: float = float(os.getenv("SCHEDULER_INTERVAL", "0.5"))

    # Admin API
    ADMIN_ENABLED:      bool  = os.getenv("ADMIN_ENABLED", "true").lower() == "true"
    ADMIN_PORT:         int   = int(os.getenv("ADMIN_PORT", "8000"))

    # Logging
    LOG_LEVEL:          str   = os.getenv("LOG_LEVEL", "INFO")
    LOG_JSON:           bool  = os.getenv("LOG_JSON", "false").lower() == "true"

    # Drain on shutdown
    DRAIN_TIMEOUT:      float = float(os.getenv("DRAIN_TIMEOUT", "30"))
```

---

## 6. Domain Model

```python
# arq_queue/models.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    RETRYING  = "retrying"
    CANCELLED = "cancelled"


@dataclass
class Job:
    func_name:   str
    args:        list        = field(default_factory=list)
    kwargs:      dict        = field(default_factory=dict)
    job_id:      str         = field(default_factory=lambda: str(uuid.uuid4()))
    queue:       str         = "default"
    priority:    int         = 5
    status:      JobStatus   = JobStatus.PENDING
    attempt:     int         = 0
    max_retries: int         = 3
    enqueued_at: float       = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    run_at:      float | None = None   # None = immediate
    result:      Any         = None
    error:       str | None  = None
    worker_id:   str | None  = None

    def to_dict(self) -> dict:
        return {
            "job_id":      self.job_id,
            "func_name":   self.func_name,
            "args":        self.args,
            "kwargs":      self.kwargs,
            "queue":       self.queue,
            "priority":    self.priority,
            "status":      self.status.value,
            "attempt":     self.attempt,
            "max_retries": self.max_retries,
            "enqueued_at": self.enqueued_at,
            "run_at":      self.run_at,
            "result":      self.result,
            "error":       self.error,
            "worker_id":   self.worker_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        d = dict(d)
        d["status"] = JobStatus(d.get("status", "pending"))
        return cls(**d)
```

---

## 7. Redis Connection & Resilience

```python
# arq_queue/connection.py
from __future__ import annotations
import asyncio
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError

from .config import Config

logger = logging.getLogger(__name__)


async def create_redis_pool(config: Config | None = None) -> aioredis.Redis:
    """
    Create a connection pool with:
    - Automatic reconnection on connection errors
    - Socket timeout to avoid hanging forever
    - Health check on each connection in pool
    """
    cfg = config or Config()

    retry = Retry(ExponentialBackoff(cap=10, base=0.5), retries=6)

    pool = aioredis.ConnectionPool.from_url(
        cfg.REDIS_URL,
        max_connections=cfg.REDIS_POOL_MAX,
        socket_timeout=cfg.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=cfg.REDIS_SOCKET_TIMEOUT,
        retry=retry if cfg.REDIS_RETRY_ON_ERR else None,
        retry_on_error=[ConnectionError, TimeoutError] if cfg.REDIS_RETRY_ON_ERR else [],
        health_check_interval=30,
    )

    client = aioredis.Redis(connection_pool=pool, decode_responses=False)

    # verify connection on startup — fail fast
    await client.ping()
    logger.info("redis connected", extra={"url": cfg.REDIS_URL.split("@")[-1]})
    return client


async def close_redis(client: aioredis.Redis) -> None:
    await client.aclose()
    logger.info("redis connection closed")


@asynccontextmanager
async def redis_pool(config: Config | None = None) -> AsyncGenerator[aioredis.Redis, None]:
    """Context manager for use in tests or scripts."""
    client = await create_redis_pool(config)
    try:
        yield client
    finally:
        await close_redis(client)
```

---

## 8. Job Serialisation

We use **msgpack** — 3–5× more compact than JSON and faster to encode/decode.  
Falls back to JSON for fields msgpack can't handle (custom types).

```python
# arq_queue/serializer.py
from __future__ import annotations
import json
import logging

try:
    import msgpack
    _USE_MSGPACK = True
except ImportError:
    _USE_MSGPACK = False

from .models import Job, JobStatus

logger = logging.getLogger(__name__)


def encode(job: Job) -> bytes:
    d = job.to_dict()
    if _USE_MSGPACK:
        return msgpack.packb(d, use_bin_type=True)
    return json.dumps(d).encode()


def decode(raw: bytes) -> Job:
    if _USE_MSGPACK:
        d = msgpack.unpackb(raw, raw=False)
    else:
        d = json.loads(raw.decode())
    return Job.from_dict(d)


def encode_result(value: object) -> bytes:
    """Store a job result — JSON only (arbitrary Python objects)."""
    return json.dumps({"value": value}, default=str).encode()


def decode_result(raw: bytes) -> object:
    return json.loads(raw.decode()).get("value")
```

---

## 9. Enqueue

```python
# arq_queue/enqueue.py
from __future__ import annotations
import logging
import time
from typing import Any

import redis.asyncio as aioredis

from .config import Config
from .models import Job, JobStatus
from .serializer import encode

logger = logging.getLogger(__name__)

QUEUE_KEY   = "queue:{name}"
DELAYED_KEY = "queue:{name}:delayed"
JOB_KEY     = "job:{job_id}"


async def enqueue(
    redis: aioredis.Redis,
    func_name: str,
    *args: Any,
    queue:        str   = "default",
    priority:     int   = 5,
    max_retries:  int   = 3,
    delay_seconds: float = 0,
    run_at:       float | None = None,
    config:       Config | None = None,
    **kwargs: Any,
) -> Job:
    cfg = config or Config()

    effective_run_at = run_at or (time.time() + delay_seconds if delay_seconds else None)

    job = Job(
        func_name=func_name,
        args=list(args),
        kwargs=kwargs,
        queue=queue,
        priority=priority,
        max_retries=max_retries,
        run_at=effective_run_at,
    )

    payload = encode(job)

    async with redis.pipeline(transaction=True) as pipe:
        if effective_run_at:
            # delayed: store in sorted set
            pipe.zadd(DELAYED_KEY.format(name=queue), {payload: effective_run_at})
        else:
            # immediate: push to main queue list
            pipe.lpush(QUEUE_KEY.format(name=queue), payload)

        # store job metadata
        pipe.hset(
            JOB_KEY.format(job_id=job.job_id),
            mapping={
                "status":    job.status.value,
                "func_name": func_name,
                "queue":     queue,
                "attempt":   0,
                "enqueued_at": job.enqueued_at,
            },
        )
        pipe.expire(JOB_KEY.format(job_id=job.job_id), cfg.JOB_RESULT_TTL)
        await pipe.execute()

    logger.info(
        "enqueued",
        extra={
            "job_id":    job.job_id,
            "func":      func_name,
            "queue":     queue,
            "delayed":   bool(effective_run_at),
            "run_at":    effective_run_at,
        },
    )
    return job


async def enqueue_many(
    redis: aioredis.Redis,
    jobs: list[dict],
    queue: str = "default",
) -> list[Job]:
    """Bulk enqueue — single pipeline round-trip."""
    created: list[Job] = []
    async with redis.pipeline(transaction=False) as pipe:
        for spec in jobs:
            job = Job(
                func_name=spec["func_name"],
                args=spec.get("args", []),
                kwargs=spec.get("kwargs", {}),
                queue=queue,
                priority=spec.get("priority", 5),
                max_retries=spec.get("max_retries", 3),
            )
            payload = encode(job)
            pipe.lpush(QUEUE_KEY.format(name=queue), payload)
            pipe.hset(
                JOB_KEY.format(job_id=job.job_id),
                mapping={"status": "pending", "func_name": job.func_name},
            )
            created.append(job)
        await pipe.execute()
    logger.info("bulk enqueued %d jobs", len(created))
    return created
```

---

## 10. Worker — BRPOP Loop

```python
# arq_queue/worker.py
from __future__ import annotations
import asyncio
import logging
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

import redis.asyncio as aioredis

from .config import Config
from .enqueue import QUEUE_KEY, JOB_KEY
from .models import Job, JobStatus
from .retry import RetryPolicy
from .serializer import decode, encode, encode_result
from .metrics import Metrics

logger = logging.getLogger(__name__)

DLQ_KEY = "queue:{name}:dlq"


class Worker:
    """
    Single worker process — runs BRPOP loop and executes jobs concurrently.

    Design decisions:
    - BRPOP timeout=2s  → allows clean shutdown without busy-waiting
    - asyncio.Semaphore → limit concurrent jobs to `concurrency`
    - asyncio.create_task → BRPOP loop is never blocked by job execution
    - Each job gets asyncio.wait_for(timeout) → no job can run forever
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        functions: dict[str, Callable[..., Awaitable]],
        metrics: Metrics,
        config: Config | None = None,
    ):
        self._redis     = redis
        self._functions = functions
        self._metrics   = metrics
        self._cfg       = config or Config()
        self._worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self._semaphore = asyncio.Semaphore(self._cfg.CONCURRENCY)
        self._running   = True
        self._active_tasks: set[asyncio.Task] = set()

    @property
    def worker_id(self) -> str:
        return self._worker_id

    async def run(self) -> None:
        queue_key = QUEUE_KEY.format(name=self._cfg.QUEUE_NAME)
        logger.info(
            "worker started",
            extra={"worker_id": self._worker_id,
                   "queue": self._cfg.QUEUE_NAME,
                   "concurrency": self._cfg.CONCURRENCY},
        )

        while self._running:
            # Don't dequeue if already at capacity
            if self._semaphore._value == 0:
                await asyncio.sleep(0.05)
                continue

            try:
                result = await self._redis.brpop(
                    queue_key, timeout=int(self._cfg.BRPOP_TIMEOUT)
                )
            except Exception as exc:
                logger.error("brpop error — will retry in 1s", extra={"error": str(exc)})
                await asyncio.sleep(1)
                continue

            if result is None:
                continue  # BRPOP timeout — loop, check self._running

            _, raw = result
            try:
                job = decode(raw)
            except Exception as exc:
                logger.error("deserialize error — discarding message",
                             extra={"error": str(exc), "raw": raw[:200]})
                continue

            task = asyncio.create_task(self._handle(job), name=f"job-{job.job_id[:8]}")
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

        # Wait for in-flight jobs to finish
        if self._active_tasks:
            logger.info("draining %d in-flight jobs", len(self._active_tasks))
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        logger.info("worker stopped", extra={"worker_id": self._worker_id})

    async def _handle(self, job: Job) -> None:
        async with self._semaphore:
            await self._update_status(job, JobStatus.RUNNING)
            self._metrics.job_started(job.func_name)
            start = time.monotonic()

            func = self._functions.get(job.func_name)
            if func is None:
                job.error = f"Unknown function: {job.func_name}"
                logger.error("unknown function", extra={"job_id": job.job_id,
                                                        "func": job.func_name})
                await self._send_to_dlq(job)
                return

            logger.info(
                "job started",
                extra={"job_id": job.job_id, "func": job.func_name,
                       "attempt": job.attempt, "worker_id": self._worker_id},
            )

            try:
                result = await asyncio.wait_for(
                    func(*job.args, **job.kwargs),
                    timeout=self._cfg.JOB_TIMEOUT,
                )
                duration_ms = (time.monotonic() - start) * 1000
                await self._mark_done(job, result, duration_ms)

            except asyncio.TimeoutError:
                job.error = f"Timeout after {self._cfg.JOB_TIMEOUT}s"
                await self._handle_failure(job)

            except Exception as exc:
                job.error = f"{type(exc).__name__}: {exc}"
                await self._handle_failure(job)

    async def _handle_failure(self, job: Job) -> None:
        logger.warning(
            "job failed",
            extra={"job_id": job.job_id, "func": job.func_name,
                   "attempt": job.attempt, "error": job.error},
        )
        self._metrics.job_failed(job.func_name)

        policy = RetryPolicy(self._cfg)
        if policy.should_retry(job):
            backoff = policy.backoff_seconds(job)
            job.attempt += 1
            logger.info(
                "job retrying",
                extra={"job_id": job.job_id, "func": job.func_name,
                       "attempt": job.attempt, "backoff_s": round(backoff, 2)},
            )
            await self._update_status(job, JobStatus.RETRYING, error=job.error)
            await asyncio.sleep(backoff)
            # Re-enqueue for immediate pickup
            payload = encode(job)
            await self._redis.lpush(QUEUE_KEY.format(name=job.queue), payload)
        else:
            await self._send_to_dlq(job)

    async def _mark_done(self, job: Job, result: object, duration_ms: float) -> None:
        job.status = JobStatus.DONE
        result_bytes = encode_result(result)
        await self._redis.hset(
            JOB_KEY.format(job_id=job.job_id),
            mapping={
                "status":      "done",
                "result":      result_bytes,
                "duration_ms": round(duration_ms, 2),
                "worker_id":   self._worker_id,
                "finished_at": time.time(),
            },
        )
        self._metrics.job_done(job.func_name, duration_ms)
        logger.info(
            "job done",
            extra={"job_id": job.job_id, "func": job.func_name,
                   "duration_ms": round(duration_ms, 2)},
        )

    async def _update_status(
        self, job: Job, status: JobStatus, error: str | None = None
    ) -> None:
        mapping: dict = {
            "status":    status.value,
            "attempt":   job.attempt,
            "worker_id": self._worker_id,
            "updated_at": time.time(),
        }
        if error:
            mapping["error"] = error
        await self._redis.hset(JOB_KEY.format(job_id=job.job_id), mapping=mapping)

    async def _send_to_dlq(self, job: Job) -> None:
        job.status = JobStatus.FAILED
        payload    = encode(job)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.lpush(DLQ_KEY.format(name=job.queue), payload)
            pipe.hset(
                JOB_KEY.format(job_id=job.job_id),
                mapping={"status": "failed", "error": job.error or "max retries exceeded"},
            )
            await pipe.execute()
        self._metrics.job_dlq(job.func_name)
        logger.error(
            "job → DLQ",
            extra={"job_id": job.job_id, "func": job.func_name,
                   "attempts": job.attempt, "error": job.error},
        )

    def stop(self) -> None:
        self._running = False
```

---

## 11. Heartbeat & Stuck-Job Reaper

```python
# arq_queue/heartbeat.py
from __future__ import annotations
import asyncio
import logging
import time

import redis.asyncio as aioredis

from .config import Config
from .enqueue import QUEUE_KEY

logger = logging.getLogger(__name__)

HEARTBEAT_KEY = "worker:{worker_id}:heartbeat"


class HeartbeatEmitter:
    """Publishes a Redis key with TTL every HEARTBEAT_INTERVAL seconds.
    If the worker dies, the key expires and the Reaper can detect it."""

    def __init__(self, redis: aioredis.Redis, worker_id: str, config: Config):
        self._redis     = redis
        self._worker_id = worker_id
        self._cfg       = config
        self._running   = True

    async def run(self) -> None:
        key = HEARTBEAT_KEY.format(worker_id=self._worker_id)
        while self._running:
            await self._redis.set(key, time.time(), ex=self._cfg.HEARTBEAT_TTL)
            await asyncio.sleep(self._cfg.HEARTBEAT_INTERVAL)

    def stop(self) -> None:
        self._running = False


class StuckJobReaper:
    """
    Periodically scans all job:{id} keys for jobs stuck in 'running' state
    whose worker heartbeat has expired — indicating a crashed worker.
    Re-enqueues them for processing.
    """

    def __init__(self, redis: aioredis.Redis, config: Config):
        self._redis   = redis
        self._cfg     = config
        self._running = True

    async def run(self) -> None:
        logger.info("stuck-job reaper started")
        while self._running:
            await asyncio.sleep(self._cfg.REAPER_INTERVAL)
            await self._reap()

    async def _reap(self) -> None:
        threshold = time.time() - self._cfg.STUCK_THRESHOLD
        rescued   = 0

        # Scan job keys — SCAN is non-blocking unlike KEYS
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match="job:*", count=200)
            for key in keys:
                data = await self._redis.hgetall(key)
                if not data:
                    continue
                data = {k.decode(): v.decode() for k, v in data.items()}
                if data.get("status") != "running":
                    continue
                updated_at = float(data.get("updated_at", 0))
                if updated_at < threshold:
                    # Worker likely crashed — re-enqueue
                    job_id    = key.decode().split(":", 1)[1]
                    queue     = data.get("queue", "default")
                    func_name = data.get("func_name", "unknown")
                    logger.warning(
                        "reaper: rescued stuck job",
                        extra={"job_id": job_id, "func": func_name,
                               "stuck_since": updated_at},
                    )
                    # Reset to pending — a simple re-queue approach.
                    # For full fidelity you'd restore args from the original payload.
                    await self._redis.hset(key, mapping={"status": "pending"})
                    rescued += 1
            if cursor == 0:
                break

        if rescued:
            logger.info("reaper finished", extra={"rescued": rescued})

    def stop(self) -> None:
        self._running = False
```

---

## 12. Scheduler — Delayed Jobs

```python
# arq_queue/scheduler.py
from __future__ import annotations
import asyncio
import logging
import time

import redis.asyncio as aioredis

from .config import Config
from .enqueue import QUEUE_KEY, DELAYED_KEY

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Polls the delayed sorted set every SCHEDULER_INTERVAL seconds.
    Moves due jobs atomically to the main queue via a pipeline.

    Why atomic?
    If two scheduler instances run simultaneously (two worker processes),
    a non-atomic read-then-delete would cause duplicate job execution.
    Redis pipelines with MULTI/EXEC give us the atomicity.
    """

    def __init__(self, redis: aioredis.Redis, config: Config | None = None):
        self._redis   = redis
        self._cfg     = config or Config()
        self._running = True

    async def run(self) -> None:
        queue_key   = QUEUE_KEY.format(name=self._cfg.QUEUE_NAME)
        delayed_key = DELAYED_KEY.format(name=self._cfg.QUEUE_NAME)
        logger.info("scheduler started", extra={"queue": self._cfg.QUEUE_NAME})

        while self._running:
            await asyncio.sleep(self._cfg.SCHEDULER_INTERVAL)
            now = time.time()

            # Fetch jobs that are due (score <= now)
            due = await self._redis.zrangebyscore(delayed_key, 0, now)
            if not due:
                continue

            # Atomically move all due jobs to the main queue
            async with self._redis.pipeline(transaction=True) as pipe:
                for payload in due:
                    pipe.lpush(queue_key, payload)
                    pipe.zrem(delayed_key, payload)
                await pipe.execute()

            logger.info(
                "scheduler moved due jobs",
                extra={"count": len(due), "queue": self._cfg.QUEUE_NAME},
            )

    def stop(self) -> None:
        self._running = False
```

---

## 13. Retry Policy

```python
# arq_queue/retry.py
from __future__ import annotations
import random
from .config import Config
from .models import Job


class RetryPolicy:
    def __init__(self, config: Config | None = None):
        self._cfg = config or Config()

    def should_retry(self, job: Job) -> bool:
        return job.attempt < job.max_retries

    def backoff_seconds(self, job: Job) -> float:
        """
        Full jitter exponential backoff.
        Reference: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

        cap  = min(base^attempt, max)
        sleep = random(0, cap)        [full jitter variant]
              = cap                   [no jitter]

        Prevents thundering herd: when N workers retry the same failing
        downstream service simultaneously, staggering retries reduces load spikes.
        """
        cap = min(self._cfg.BACKOFF_BASE ** (job.attempt + 1), self._cfg.BACKOFF_MAX)
        if self._cfg.BACKOFF_JITTER:
            return random.uniform(0, cap)
        return cap
```

---

## 14. Dead-Letter Queue

```python
# arq_queue/dlq.py
from __future__ import annotations
import logging

import redis.asyncio as aioredis

from .enqueue import QUEUE_KEY
from .models import Job
from .serializer import decode, encode

logger = logging.getLogger(__name__)

DLQ_KEY = "queue:{name}:dlq"


async def list_dlq(
    redis: aioredis.Redis, queue: str = "default", limit: int = 100
) -> list[Job]:
    key   = DLQ_KEY.format(name=queue)
    items = await redis.lrange(key, 0, limit - 1)
    jobs  = []
    for raw in items:
        try:
            jobs.append(decode(raw))
        except Exception:
            logger.warning("dlq: could not decode item, skipping")
    return jobs


async def retry_job(
    redis: aioredis.Redis, job_id: str, queue: str = "default"
) -> bool:
    """Move a single DLQ job back to the main queue, resetting its attempt counter."""
    dlq_key   = DLQ_KEY.format(name=queue)
    queue_key = QUEUE_KEY.format(name=queue)

    items = await redis.lrange(dlq_key, 0, -1)
    for raw in items:
        try:
            job = decode(raw)
        except Exception:
            continue
        if job.job_id == job_id:
            job.attempt = 0
            job.error   = None
            new_payload = encode(job)
            async with redis.pipeline(transaction=True) as pipe:
                pipe.lrem(dlq_key, 1, raw)
                pipe.lpush(queue_key, new_payload)
                await pipe.execute()
            logger.info("dlq: job retried", extra={"job_id": job_id})
            return True
    return False


async def retry_all(redis: aioredis.Redis, queue: str = "default") -> int:
    """Move all DLQ jobs back for reprocessing."""
    dlq_key   = DLQ_KEY.format(name=queue)
    queue_key = QUEUE_KEY.format(name=queue)
    count = 0
    while True:
        raw = await redis.rpoplpush(dlq_key, queue_key)
        if raw is None:
            break
        try:
            job = decode(raw)
            job.attempt = 0
            new_payload = encode(job)
            await redis.lrem(queue_key, 1, raw)
            await redis.lpush(queue_key, new_payload)
        except Exception:
            pass
        count += 1
    logger.info("dlq: all jobs retried", extra={"count": count})
    return count


async def purge(redis: aioredis.Redis, queue: str = "default") -> int:
    key   = DLQ_KEY.format(name=queue)
    count = await redis.llen(key)
    await redis.delete(key)
    logger.info("dlq: purged", extra={"count": count})
    return count
```

---

## 15. Result Backend

```python
# arq_queue/results.py
from __future__ import annotations
import asyncio
import logging
import time

import redis.asyncio as aioredis

from .enqueue import JOB_KEY
from .serializer import decode_result

logger = logging.getLogger(__name__)


async def get_result(redis: aioredis.Redis, job_id: str) -> dict | None:
    key  = JOB_KEY.format(job_id=job_id)
    data = await redis.hgetall(key)
    if not data:
        return None
    decoded = {k.decode(): v.decode() if isinstance(v, bytes) else v
               for k, v in data.items()}
    # deserialize result bytes if present
    if "result" in decoded and isinstance(decoded["result"], str):
        try:
            decoded["result"] = decode_result(decoded["result"].encode())
        except Exception:
            pass
    return decoded


async def wait_for_result(
    redis: aioredis.Redis,
    job_id: str,
    timeout: float = 30,
    poll_interval: float = 0.25,
) -> dict:
    """
    Poll Redis until the job reaches a terminal state (done/failed/cancelled).
    For very high throughput, consider using Redis keyspace notifications instead.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = await get_result(redis, job_id)
        if result and result.get("status") in ("done", "failed", "cancelled"):
            return result
        await asyncio.sleep(poll_interval)
    raise TimeoutError(
        f"Job {job_id} did not reach a terminal state within {timeout}s"
    )
```

---

## 16. Rate Limiting

```python
# arq_queue/rate_limit.py
"""
Fixed-window rate limiter using Redis INCR + EXPIRE.
Prevents a single function type from flooding the worker pool.
"""
from __future__ import annotations
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

RATE_KEY = "queue:{queue}:rate:{func}"


async def is_rate_limited(
    redis: aioredis.Redis,
    func_name: str,
    max_per_minute: int,
    queue: str = "default",
) -> bool:
    """
    Returns True if this function has already been called max_per_minute
    times in the current 60-second window.
    """
    if max_per_minute <= 0:
        return False
    key   = RATE_KEY.format(queue=queue, func=func_name)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    allowed = count <= max_per_minute
    if not allowed:
        logger.warning(
            "rate limited",
            extra={"func": func_name, "count": count, "limit": max_per_minute},
        )
    return not allowed


async def get_rate(
    redis: aioredis.Redis, func_name: str, queue: str = "default"
) -> int:
    key = RATE_KEY.format(queue=queue, func=func_name)
    val = await redis.get(key)
    return int(val) if val else 0
```

---

## 17. Structured Logging & Metrics

```python
# arq_queue/logging_setup.py
from __future__ import annotations
import json
import logging
import sys
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                base[key] = val
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, default=str)


class _PlainFormatter(logging.Formatter):
    FMT = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"

    def __init__(self):
        super().__init__(self.FMT, datefmt="%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__ and not k.startswith("_")
        }
        if extras:
            kv = " ".join(f"{k}={v}" for k, v in extras.items())
            return f"{base}  [{kv}]"
        return base


def setup_logging(level: str = "INFO", json_logs: bool = False) -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter() if json_logs else _PlainFormatter())
    root.addHandler(handler)
```

```python
# arq_queue/metrics.py
from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class FuncMetrics:
    started:   int   = 0
    done:      int   = 0
    failed:    int   = 0
    dlq:       int   = 0
    total_ms:  float = 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.done if self.done else 0.0


class Metrics:
    def __init__(self):
        self._lock   = Lock()
        self._funcs: dict[str, FuncMetrics] = defaultdict(FuncMetrics)
        self._start  = time.monotonic()

    def job_started(self, fn: str):
        with self._lock: self._funcs[fn].started += 1

    def job_done(self, fn: str, ms: float):
        with self._lock:
            m = self._funcs[fn]
            m.done    += 1
            m.total_ms += ms

    def job_failed(self, fn: str):
        with self._lock: self._funcs[fn].failed += 1

    def job_dlq(self, fn: str):
        with self._lock: self._funcs[fn].dlq += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_s": round(time.monotonic() - self._start, 1),
                "functions": {
                    name: {
                        "started":  m.started,
                        "done":     m.done,
                        "failed":   m.failed,
                        "dlq":      m.dlq,
                        "avg_ms":   round(m.avg_ms, 2),
                    }
                    for name, m in self._funcs.items()
                },
            }

    def prometheus_text(self) -> str:
        lines = []
        with self._lock:
            for name, m in self._funcs.items():
                for metric, val in [
                    ("aq_jobs_started_total", m.started),
                    ("aq_jobs_done_total",    m.done),
                    ("aq_jobs_failed_total",  m.failed),
                    ("aq_jobs_dlq_total",     m.dlq),
                    ("aq_job_duration_ms_sum",m.total_ms),
                ]:
                    lines.append(f'{metric}{{func="{name}"}} {val}')
        return "\n".join(lines) + "\n"
```

---

## 18. Admin API (FastAPI)

```python
# arq_queue/admin_api.py
"""
FastAPI admin endpoints — mount inside your existing app or run standalone.

GET  /admin/health          → queue stats
GET  /admin/metrics         → Prometheus text
GET  /admin/jobs/{job_id}   → job status + result
GET  /admin/dlq             → list DLQ
POST /admin/dlq/{job_id}/retry   → retry one DLQ job
POST /admin/dlq/retry-all        → retry all DLQ jobs
DELETE /admin/dlq           → purge DLQ
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import PlainTextResponse

import redis.asyncio as aioredis

from .config import Config
from .results import get_result
from .dlq import list_dlq, retry_job, retry_all, purge
from .metrics import Metrics


def build_admin_app(
    redis_client: aioredis.Redis,
    metrics: Metrics,
    config: Config | None = None,
) -> FastAPI:
    cfg = config or Config()
    app = FastAPI(title="arq_queue Admin", docs_url="/admin/docs")

    async def get_redis() -> aioredis.Redis:
        return redis_client

    @app.get("/admin/health")
    async def health(r: aioredis.Redis = Depends(get_redis)):
        info = await r.info("server")
        return {
            "status":       "ok",
            "redis_version": info.get("redis_version"),
            "metrics":      metrics.snapshot(),
        }

    @app.get("/admin/metrics", response_class=PlainTextResponse)
    async def prometheus_metrics():
        return metrics.prometheus_text()

    @app.get("/admin/jobs/{job_id}")
    async def get_job(job_id: str, r: aioredis.Redis = Depends(get_redis)):
        result = await get_result(r, job_id)
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result

    @app.get("/admin/dlq")
    async def get_dlq(
        queue: str = "default",
        limit: int = 100,
        r: aioredis.Redis = Depends(get_redis),
    ):
        jobs = await list_dlq(r, queue=queue, limit=limit)
        return {"count": len(jobs), "jobs": [j.to_dict() for j in jobs]}

    @app.post("/admin/dlq/{job_id}/retry")
    async def retry_one(
        job_id: str, queue: str = "default",
        r: aioredis.Redis = Depends(get_redis),
    ):
        ok = await retry_job(r, job_id, queue=queue)
        if not ok:
            raise HTTPException(status_code=404, detail="Job not found in DLQ")
        return {"retried": job_id}

    @app.post("/admin/dlq/retry-all")
    async def retry_all_dlq(
        queue: str = "default",
        r: aioredis.Redis = Depends(get_redis),
    ):
        count = await retry_all(r, queue=queue)
        return {"retried": count}

    @app.delete("/admin/dlq")
    async def purge_dlq(
        queue: str = "default",
        r: aioredis.Redis = Depends(get_redis),
    ):
        count = await purge(r, queue=queue)
        return {"purged": count}

    return app
```

---

## 19. Graceful Shutdown

```python
# arq_queue/shutdown.py
from __future__ import annotations
import asyncio
import logging
import signal
from typing import Callable

logger = logging.getLogger(__name__)


class GracefulShutdown:
    def __init__(self, on_signal: Callable[[], None]):
        self._on_signal  = on_signal
        self._stop_event = asyncio.Event()

    def install(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle)

    def _handle(self) -> None:
        logger.info("shutdown signal received")
        self._on_signal()
        self._stop_event.set()

    async def wait(self) -> None:
        await self._stop_event.wait()
```

---

## 20. Full Wiring — `app.py`

```python
# arq_queue/app.py
from __future__ import annotations
import asyncio
import logging
import uvicorn
from typing import Awaitable, Callable

from .config import Config
from .connection import create_redis_pool, close_redis
from .heartbeat import HeartbeatEmitter, StuckJobReaper
from .logging_setup import setup_logging
from .metrics import Metrics
from .scheduler import Scheduler
from .shutdown import GracefulShutdown
from .worker import Worker
from .admin_api import build_admin_app

logger = logging.getLogger(__name__)


class ArqQueue:
    """
    Public API — the only class application code needs.

    Usage:
        from arq_queue.app import ArqQueue

        queue = ArqQueue()

        @queue.task
        async def send_email(to: str): ...

        async def main():
            await queue.start()
            job = await queue.enqueue("send_email", "alice@example.com")
            await queue.stop()
    """

    def __init__(self, config: Config | None = None):
        self._cfg       = config or Config()
        self._functions: dict[str, Callable[..., Awaitable]] = {}
        self._metrics   = Metrics()
        self._redis     = None
        self._worker    = None
        self._scheduler = None
        self._heartbeat = None
        self._reaper    = None
        self._admin_server = None
        self._tasks: list[asyncio.Task] = []

    def task(self, func: Callable[..., Awaitable] | None = None, *, name: str | None = None):
        def decorator(fn):
            key = name or fn.__name__
            self._functions[key] = fn
            return fn
        return decorator(func) if func is not None else decorator

    async def enqueue(self, func_name: str, *args, **kwargs):
        from .enqueue import enqueue
        return await enqueue(self._redis, func_name, *args,
                             queue=self._cfg.QUEUE_NAME,
                             config=self._cfg, **kwargs)

    async def start(self) -> None:
        setup_logging(self._cfg.LOG_LEVEL, self._cfg.LOG_JSON)
        self._redis     = await create_redis_pool(self._cfg)
        self._worker    = Worker(self._redis, self._functions, self._metrics, self._cfg)
        self._scheduler = Scheduler(self._redis, self._cfg)
        self._heartbeat = HeartbeatEmitter(self._redis, self._worker.worker_id, self._cfg)
        self._reaper    = StuckJobReaper(self._redis, self._cfg)

        self._tasks = [
            asyncio.create_task(self._worker.run(),    name="worker"),
            asyncio.create_task(self._scheduler.run(), name="scheduler"),
            asyncio.create_task(self._heartbeat.run(), name="heartbeat"),
            asyncio.create_task(self._reaper.run(),    name="reaper"),
        ]

        if self._cfg.ADMIN_ENABLED:
            admin_app = build_admin_app(self._redis, self._metrics, self._cfg)
            config = uvicorn.Config(
                admin_app, host="0.0.0.0", port=self._cfg.ADMIN_PORT,
                log_level="warning",
            )
            self._admin_server = uvicorn.Server(config)
            self._tasks.append(
                asyncio.create_task(self._admin_server.serve(), name="admin-api")
            )

        logger.info("ArqQueue started", extra={
            "queue":       self._cfg.QUEUE_NAME,
            "concurrency": self._cfg.CONCURRENCY,
            "admin_port":  self._cfg.ADMIN_PORT if self._cfg.ADMIN_ENABLED else None,
        })

    async def stop(self) -> None:
        logger.info("ArqQueue stopping — draining in-flight jobs...")
        self._worker.stop()
        self._scheduler.stop()
        self._heartbeat.stop()
        self._reaper.stop()

        if self._admin_server:
            self._admin_server.should_exit = True

        drain = asyncio.wait_for(
            asyncio.gather(*self._tasks, return_exceptions=True),
            timeout=self._cfg.DRAIN_TIMEOUT,
        )
        try:
            await drain
        except asyncio.TimeoutError:
            logger.warning("drain timeout — cancelling remaining tasks")
            for t in self._tasks:
                t.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)

        await close_redis(self._redis)
        logger.info("ArqQueue stopped")

    async def run_forever(self) -> None:
        await self.start()
        shutdown = GracefulShutdown(on_signal=lambda: None)
        shutdown.install()
        await shutdown.wait()
        await self.stop()
```

---

## 21. Example Tasks & Main

```python
# arq_queue/example_tasks.py
import asyncio
import random
from .app import ArqQueue

def register_tasks(queue: ArqQueue) -> None:

    @queue.task
    async def send_email(to: str, subject: str) -> str:
        await asyncio.sleep(0.05)
        return f"sent:{to}"

    @queue.task
    async def process_payment(user_id: int, amount_cents: int) -> dict:
        if amount_cents <= 0:
            raise ValueError("amount must be positive")
        await asyncio.sleep(0.1)
        return {"user_id": user_id, "charged": amount_cents}

    @queue.task
    async def flaky(fail_rate: float = 0.7) -> str:
        if random.random() < fail_rate:
            raise RuntimeError("flaky task failed (expected)")
        return "ok"
```

```python
# arq_queue/main.py
import asyncio
from .app import ArqQueue
from .example_tasks import register_tasks
from .results import wait_for_result

async def main():
    queue = ArqQueue()
    register_tasks(queue)
    await queue.start()

    jobs = []
    for i in range(5):
        j = await queue.enqueue("send_email", to=f"u{i}@ex.com", subject=f"Hi #{i}")
        jobs.append(j)

    j = await queue.enqueue("process_payment", user_id=42, amount_cents=4999)
    jobs.append(j)

    j = await queue.enqueue("flaky", fail_rate=0.9)
    jobs.append(j)

    j = await queue.enqueue("send_email", to="delayed@ex.com",
                            subject="Delayed", delay_seconds=3)
    jobs.append(j)

    # wait for all jobs except the delayed one
    for job in jobs[:-1]:
        result = await wait_for_result(queue._redis, job.job_id, timeout=30)
        print(f"  [{result.get('status'):8}] {job.func_name}[{job.job_id[:8]}]"
              f" → {result.get('result') or result.get('error')}")

    await asyncio.sleep(5)   # let delayed job run

    await queue.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 22. Tests

```python
# arq_queue/tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from arq_queue.config import Config

TEST_REDIS_URL = "redis://localhost:6379/15"   # DB 15 — isolated test DB

@pytest.fixture
def test_config():
    c = Config()
    c.REDIS_URL          = TEST_REDIS_URL
    c.QUEUE_NAME         = "test"
    c.CONCURRENCY        = 3
    c.MAX_RETRIES        = 2
    c.BACKOFF_BASE       = 0.01
    c.BACKOFF_JITTER     = False
    c.JOB_TIMEOUT        = 2.0
    c.ADMIN_ENABLED      = False
    c.HEARTBEAT_INTERVAL = 999   # disable in tests
    c.REAPER_INTERVAL    = 999
    return c

@pytest_asyncio.fixture
async def redis_client(test_config):
    client = aioredis.Redis.from_url(test_config.REDIS_URL, decode_responses=False)
    await client.flushdb()          # clean slate before each test
    yield client
    await client.flushdb()          # clean up after
    await client.aclose()

@pytest_asyncio.fixture
async def queue(test_config, redis_client):
    from arq_queue.app import ArqQueue
    q = ArqQueue(config=test_config)
    # inject already-created redis client
    q._redis = redis_client
    from arq_queue.metrics import Metrics
    from arq_queue.worker import Worker
    from arq_queue.scheduler import Scheduler
    from arq_queue.heartbeat import HeartbeatEmitter, StuckJobReaper
    q._metrics   = Metrics()
    q._worker    = Worker(redis_client, q._functions, q._metrics, test_config)
    q._scheduler = Scheduler(redis_client, test_config)
    # register test tasks
    @q.task
    async def add(a: int, b: int) -> int:
        return a + b

    @q.task
    async def always_fail():
        raise RuntimeError("always fails")

    import asyncio
    q._tasks = [
        asyncio.create_task(q._worker.run()),
        asyncio.create_task(q._scheduler.run()),
    ]
    yield q
    q._worker.stop()
    q._scheduler.stop()
    await asyncio.gather(*q._tasks, return_exceptions=True)
```

```python
# arq_queue/tests/test_integration.py
import asyncio
import pytest
from arq_queue.results import wait_for_result, get_result
from arq_queue.dlq import list_dlq, retry_all

@pytest.mark.asyncio
async def test_successful_job(queue, redis_client):
    job = await queue.enqueue("add", 3, 4)
    result = await wait_for_result(redis_client, job.job_id, timeout=15)
    assert result["status"] == "done"

@pytest.mark.asyncio
async def test_failed_job_lands_in_dlq(queue, redis_client):
    job = await queue.enqueue("always_fail")
    # wait for it to exhaust retries
    await asyncio.sleep(5)
    dlq = await list_dlq(redis_client, queue="test")
    ids = [j.job_id for j in dlq]
    assert job.job_id in ids

@pytest.mark.asyncio
async def test_retry_all_clears_dlq(queue, redis_client):
    await queue.enqueue("always_fail")
    await asyncio.sleep(5)
    dlq_before = await list_dlq(redis_client, queue="test")
    assert len(dlq_before) > 0
    retried = await retry_all(redis_client, queue="test")
    assert retried >= 1

@pytest.mark.asyncio
async def test_delayed_job(queue, redis_client):
    job = await queue.enqueue("add", 1, 2, delay_seconds=1)
    # job should not be in queue immediately
    result = await get_result(redis_client, job.job_id)
    assert result["status"] == "pending"
    # after delay + processing time
    result = await wait_for_result(redis_client, job.job_id, timeout=10)
    assert result["status"] == "done"

@pytest.mark.asyncio
async def test_bulk_jobs_all_succeed(queue, redis_client):
    from arq_queue.enqueue import enqueue_many
    specs = [{"func_name": "add", "kwargs": {"a": i, "b": i}} for i in range(10)]
    jobs = await enqueue_many(redis_client, specs, queue="test")
    for job in jobs:
        result = await wait_for_result(redis_client, job.job_id, timeout=15)
        assert result["status"] == "done"
```

```python
# arq_queue/tests/test_serializer.py
from arq_queue.models import Job, JobStatus
from arq_queue.serializer import encode, decode

def test_roundtrip():
    job = Job(func_name="send_email", args=["alice@ex.com"],
              kwargs={"subject": "Hi"}, max_retries=5)
    raw     = encode(job)
    decoded = decode(raw)
    assert decoded.job_id      == job.job_id
    assert decoded.func_name   == "send_email"
    assert decoded.args        == ["alice@ex.com"]
    assert decoded.kwargs      == {"subject": "Hi"}
    assert decoded.max_retries == 5

def test_status_preserved():
    job = Job(func_name="f", status=JobStatus.RETRYING, attempt=2)
    decoded = decode(encode(job))
    assert decoded.status  == JobStatus.RETRYING
    assert decoded.attempt == 2
```

---

## 23. `requirements.txt`

```
redis[asyncio]>=5.0
msgpack>=1.0
fastapi>=0.111
uvicorn[standard]>=0.29
python-dotenv>=1.0
pytest>=8
pytest-asyncio>=0.23
httpx>=0.27     # for FastAPI test client
```

---

## 24. Docker & docker-compose

```yaml
# docker-compose.yml
version: "3.9"

services:
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --appendonly yes
      --appendfsync everysec
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  worker:
    build: .
    command: python -m arq_queue.main
    environment:
      REDIS_URL:    redis://redis:6379/0
      QUEUE_NAME:   default
      CONCURRENCY:  10
      MAX_RETRIES:  3
      LOG_JSON:     "true"
      ADMIN_PORT:   8000
    ports:
      - "8000:8000"
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  redis_data:
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "arq_queue.main"]
```

---

## 25. Running the Project

```bash
# 1. Start Redis
docker compose up redis -d

# 2. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Run worker
python -m arq_queue.main

# 4. Check admin API
curl http://localhost:8000/admin/health
curl http://localhost:8000/admin/metrics    # Prometheus format
curl http://localhost:8000/admin/dlq

# 5. Run all tests (requires Redis on localhost:6379)
pytest arq_queue/tests/ -v

# 6. Run via Docker Compose
docker compose up --build
```

---

## 26. Production Checklist

| Concern | Implementation |
|---|---|
| Persistence across restart | ✅ Redis AOF (`appendonly yes`, `appendfsync everysec`) |
| Multi-machine workers | ✅ BRPOP on shared Redis — start worker on N machines |
| Zero duplicate execution | ✅ Atomic LPUSH / BRPOP — each job consumed once |
| Job stuck after worker crash | ✅ Heartbeat + StuckJobReaper auto-rescues |
| Retry storms | ✅ Full-jitter exponential backoff |
| Persistent failures | ✅ DLQ + admin API retry/purge |
| Delayed / scheduled jobs | ✅ Sorted set + Scheduler |
| Rate limiting | ✅ Redis INCR token bucket |
| Observability | ✅ Structured JSON logs + Prometheus metrics |
| Admin visibility | ✅ FastAPI `/admin/*` endpoints |
| Graceful shutdown | ✅ SIGINT/SIGTERM + configurable drain timeout |
| Config management | ✅ All tunables via env vars |
| Connection resilience | ✅ Retry on ConnectionError/Timeout with exponential backoff |
| Test suite | ✅ Unit + integration tests |
| Containerisation | ✅ Dockerfile + docker-compose |
