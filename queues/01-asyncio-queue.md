# Building a Production-Grade In-Process Async Queue — `asyncio.Queue`

> **Level:** Beginner → Production  
> **Python:** 3.11+  
> **Dependencies:** stdlib only (`asyncio`, `logging`, `signal`, `dataclasses`, `enum`)  
> **What you will build:** A fully typed, observable, gracefully-shutdown-aware in-process async
> job queue with worker pool, priority support, retries, dead-letter storage, structured logging,
> Prometheus-compatible metrics, a health-check HTTP endpoint, and a full test suite.

---

## Table of Contents

1. [How `asyncio.Queue` Works Internally](#1-how-asyncioqueue-works-internally)
2. [Project Layout](#2-project-layout)
3. [Configuration](#3-configuration)
4. [Domain Model — `Job`](#4-domain-model--job)
5. [Function Registry](#5-function-registry)
6. [The Queue Engine](#6-the-queue-engine)
7. [Worker Pool](#7-worker-pool)
8. [Retry & Dead-Letter](#8-retry--dead-letter)
9. [Structured Logging](#9-structured-logging)
10. [Metrics](#10-metrics)
11. [Health-Check HTTP Server](#11-health-check-http-server)
12. [Graceful Shutdown](#12-graceful-shutdown)
13. [Putting It All Together — `engine.py`](#13-putting-it-all-together--enginepy)
14. [Tests](#14-tests)
15. [Running the Project](#15-running-the-project)
16. [Production Checklist](#16-production-checklist)
17. [Limitations & When to Graduate to Redis/PostgreSQL](#17-limitations--when-to-graduate-to-redispostgresql)

---

## 1. How `asyncio.Queue` Works Internally

`asyncio.Queue` is **not** thread-safe — it is **coroutine-safe**.  
It never touches a thread lock. It operates entirely within a single OS thread's event loop.

```
asyncio.Queue internals
──────────────────────────────────────────────────────────────────
  _queue      collections.deque     the stored items
  _getters    list[asyncio.Future]  coroutines waiting to GET
  _putters    list[asyncio.Future]  coroutines waiting to PUT
  _unfinished_tasks  int            incremented on put, decremented on task_done()
──────────────────────────────────────────────────────────────────
```

### `put(item)` flow

```
await q.put(item)
  │
  ├─ len(_queue) < maxsize  ──► deque.append(item)
  │                              if _getters: resolve first getter Future
  │
  └─ len(_queue) == maxsize ──► create Future, append to _putters
                                 suspend this coroutine
                                 (resumed when a consumer calls get())
```

### `get()` flow

```
await q.get()
  │
  ├─ _queue not empty ──► item = deque.popleft()
  │                        if _putters: resolve first putter Future
  │
  └─ _queue empty     ──► create Future, append to _getters
                           suspend this coroutine
                           (resumed when a producer calls put())
```

### `task_done()` / `join()` protocol

```
Every put()  → _unfinished_tasks += 1
Every task_done() → _unfinished_tasks -= 1
                    if _unfinished_tasks == 0 → resolve join() Future
```

> **Key insight:** `asyncio.Queue` never blocks a thread.  
> Suspension means "give control back to the event loop until the condition is met."

---

## 2. Project Layout

```
asyncio_queue/
├── config.py          # all tunables in one place (env-driven)
├── models.py          # Job dataclass + JobStatus enum
├── registry.py        # @register decorator + function lookup
├── queue_engine.py    # QueueEngine — the main queue class
├── worker.py          # WorkerPool — spawns and manages worker coroutines
├── retry.py           # retry policy, backoff calculator, DLQ
├── logging_setup.py   # structured JSON logging
├── metrics.py         # in-process Prometheus-style counters
├── health.py          # tiny aiohttp health-check server
├── shutdown.py        # SIGINT/SIGTERM handler with drain
├── engine.py          # wires everything together — the public API
├── example_tasks.py   # sample registered functions
├── main.py            # entry point
└── tests/
    ├── test_models.py
    ├── test_queue_engine.py
    ├── test_worker.py
    ├── test_retry.py
    └── test_integration.py
```

---

## 3. Configuration

All tunables come from environment variables with sensible defaults.  
Never hardcode numbers — operators need to tune without redeploying.

```python
# asyncio_queue/config.py
from __future__ import annotations
import os

class Config:
    # Worker pool
    NUM_WORKERS:        int   = int(os.getenv("AQ_NUM_WORKERS",   "4"))
    QUEUE_MAXSIZE:      int   = int(os.getenv("AQ_MAXSIZE",       "1000"))
    USE_PRIORITY:       bool  = os.getenv("AQ_PRIORITY", "false").lower() == "true"

    # Job execution
    JOB_TIMEOUT:        float = float(os.getenv("AQ_JOB_TIMEOUT", "60"))

    # Retry policy
    MAX_RETRIES:        int   = int(os.getenv("AQ_MAX_RETRIES",   "3"))
    BACKOFF_BASE:       float = float(os.getenv("AQ_BACKOFF_BASE","2.0"))
    BACKOFF_MAX:        float = float(os.getenv("AQ_BACKOFF_MAX", "60.0"))
    BACKOFF_JITTER:     bool  = os.getenv("AQ_JITTER", "true").lower() == "true"

    # Dead-letter
    DLQ_MAXSIZE:        int   = int(os.getenv("AQ_DLQ_MAXSIZE",  "500"))

    # Health check
    HEALTH_PORT:        int   = int(os.getenv("AQ_HEALTH_PORT",  "8080"))
    HEALTH_ENABLED:     bool  = os.getenv("AQ_HEALTH_ENABLED","true").lower() == "true"

    # Logging
    LOG_LEVEL:          str   = os.getenv("AQ_LOG_LEVEL",        "INFO")
    LOG_JSON:           bool  = os.getenv("AQ_LOG_JSON",  "false").lower() == "true"

    # Drain timeout on shutdown
    DRAIN_TIMEOUT:      float = float(os.getenv("AQ_DRAIN_TIMEOUT","30.0"))
```

---

## 4. Domain Model — `Job`

```python
# asyncio_queue/models.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable


class JobStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class Job:
    # identity
    job_id:      str      = field(default_factory=lambda: str(uuid.uuid4()))
    func_name:   str      = ""

    # payload  (func is NOT serialised — it lives in the registry)
    func:        Callable[..., Awaitable[Any]] | None = field(default=None, repr=False)
    args:        tuple    = field(default_factory=tuple)
    kwargs:      dict     = field(default_factory=dict)

    # routing
    queue:       str      = "default"
    priority:    int      = 5           # lower = higher priority

    # lifecycle
    status:      JobStatus = JobStatus.PENDING
    attempt:     int       = 0
    max_retries: int       = 3

    # timing
    enqueued_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at:   datetime | None = None
    finished_at:  datetime | None = None

    # output
    result:  Any        = None
    error:   str | None = None

    # for PriorityQueue ordering — compare only on priority
    def __lt__(self, other: "Job") -> bool:
        return self.priority < other.priority

    def __le__(self, other: "Job") -> bool:
        return self.priority <= other.priority

    @property
    def duration_ms(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return None

    def to_dict(self) -> dict:
        return {
            "job_id":      self.job_id,
            "func_name":   self.func_name,
            "queue":       self.queue,
            "priority":    self.priority,
            "status":      self.status.value,
            "attempt":     self.attempt,
            "max_retries": self.max_retries,
            "enqueued_at": self.enqueued_at.isoformat(),
            "started_at":  self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "result":      str(self.result) if self.result is not None else None,
            "error":       self.error,
        }
```

---

## 5. Function Registry

Workers can only call functions they know about.  
The registry maps `func_name → coroutine function`.

```python
# asyncio_queue/registry.py
from __future__ import annotations
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Callable[..., Awaitable]] = {}


def register(func: Callable[..., Awaitable] | None = None, *, name: str | None = None):
    """
    Decorator — register an async function so workers can call it by name.

    Usage:
        @register
        async def send_email(to: str): ...

        @register(name="my_custom_name")
        async def process_order(order_id: int): ...
    """
    def decorator(fn: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        key = name or fn.__name__
        if key in _REGISTRY:
            logger.warning("registry: overwriting existing function '%s'", key)
        _REGISTRY[key] = fn
        logger.debug("registry: registered '%s'", key)
        return fn

    if func is not None:
        # called as @register (no args)
        return decorator(func)
    # called as @register(name="...")
    return decorator


def get(func_name: str) -> Callable[..., Awaitable] | None:
    return _REGISTRY.get(func_name)


def all_names() -> list[str]:
    return list(_REGISTRY.keys())


def register_many(mapping: dict[str, Callable[..., Awaitable]]) -> None:
    for name, fn in mapping.items():
        _REGISTRY[name] = fn
```

---

## 6. The Queue Engine

The `QueueEngine` wraps `asyncio.Queue` (or `asyncio.PriorityQueue`) and provides:
- Typed `enqueue()` / `dequeue()` API  
- In-memory result store  
- DLQ storage  
- Size/status snapshots for monitoring  

```python
# asyncio_queue/queue_engine.py
from __future__ import annotations
import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any

from .config import Config
from .models import Job, JobStatus

logger = logging.getLogger(__name__)


class QueueEngine:
    """
    Thread-unsafe, coroutine-safe queue engine backed by asyncio.Queue.
    All public methods must be called from the same event loop.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or Config()
        self._cfg         = cfg
        self._use_priority = cfg.USE_PRIORITY

        if cfg.USE_PRIORITY:
            self._q: asyncio.Queue[Job | tuple[int, Job]] = asyncio.PriorityQueue(
                maxsize=cfg.QUEUE_MAXSIZE
            )
        else:
            self._q = asyncio.Queue(maxsize=cfg.QUEUE_MAXSIZE)

        # in-memory result store: job_id → Job
        self._results: dict[str, Job] = {}

        # dead letter queue (capped deque — evicts oldest on overflow)
        self._dlq: deque[Job] = deque(maxlen=cfg.DLQ_MAXSIZE)

        # running jobs: job_id → Job (for status checks)
        self._running: dict[str, Job] = {}

    # ── Enqueue ───────────────────────────────────────────────────────────

    async def enqueue(
        self,
        func_name: str,
        *args: Any,
        priority: int = 5,
        max_retries: int | None = None,
        queue: str = "default",
        **kwargs: Any,
    ) -> Job:
        from . import registry
        func = registry.get(func_name)
        if func is None:
            raise ValueError(
                f"Function '{func_name}' is not registered. "
                f"Available: {registry.all_names()}"
            )

        job = Job(
            func_name=func_name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries if max_retries is not None else self._cfg.MAX_RETRIES,
            queue=queue,
        )
        self._results[job.job_id] = job

        item = (priority, job) if self._use_priority else job
        await self._q.put(item)   # suspends if queue is full (backpressure)

        logger.info(
            "enqueued",
            extra={"job_id": job.job_id, "func": func_name,
                   "priority": priority, "qsize": self._q.qsize()},
        )
        return job

    def enqueue_nowait(self, func_name: str, *args: Any, **kwargs: Any) -> Job:
        """Non-blocking enqueue. Raises QueueFull if at capacity."""
        from . import registry
        func = registry.get(func_name)
        if func is None:
            raise ValueError(f"Function '{func_name}' not registered.")
        job = Job(func_name=func_name, func=func, args=args, kwargs=kwargs)
        self._results[job.job_id] = job
        item = (job.priority, job) if self._use_priority else job
        self._q.put_nowait(item)
        return job

    # ── Dequeue (used by workers) ─────────────────────────────────────────

    async def dequeue(self) -> Job:
        item = await self._q.get()
        job  = item[1] if self._use_priority else item
        job.status     = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        self._running[job.job_id] = job
        return job

    def task_done(self, job: Job) -> None:
        self._running.pop(job.job_id, None)
        self._q.task_done()

    # ── DLQ ───────────────────────────────────────────────────────────────

    def send_to_dlq(self, job: Job) -> None:
        job.status      = JobStatus.FAILED
        job.finished_at = datetime.now(timezone.utc)
        self._dlq.append(job)
        logger.error(
            "job moved to DLQ",
            extra={"job_id": job.job_id, "func": job.func_name,
                   "attempts": job.attempt, "error": job.error},
        )

    async def retry(self, job: Job, backoff: float) -> None:
        job.status  = JobStatus.RETRYING
        job.attempt += 1
        self._running.pop(job.job_id, None)
        self._q.task_done()
        await asyncio.sleep(backoff)
        item = (job.priority, job) if self._use_priority else job
        await self._q.put(item)

    # ── Queries ───────────────────────────────────────────────────────────

    def get_job(self, job_id: str) -> Job | None:
        return self._results.get(job_id)

    def dlq_jobs(self) -> list[Job]:
        return list(self._dlq)

    def stats(self) -> dict:
        status_counts: dict[str, int] = {}
        for job in self._results.values():
            key = job.status.value
            status_counts[key] = status_counts.get(key, 0) + 1
        return {
            "pending":  self._q.qsize(),
            "running":  len(self._running),
            "dlq_size": len(self._dlq),
            "total":    len(self._results),
            "by_status": status_counts,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def join(self) -> None:
        """Wait until every enqueued job has been processed."""
        await self._q.join()
```

---

## 7. Worker Pool

```python
# asyncio_queue/worker.py
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone

from .config import Config
from .models import Job, JobStatus
from .queue_engine import QueueEngine
from .retry import RetryPolicy
from .metrics import Metrics

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Spawns N worker coroutines that consume jobs from QueueEngine.
    Each worker:
      1. dequeues a job
      2. runs it with a timeout
      3. on success  → marks done, records metrics
      4. on failure  → delegates to RetryPolicy (retry or DLQ)
    """

    def __init__(
        self,
        engine: QueueEngine,
        metrics: Metrics,
        config: Config | None = None,
    ):
        self._engine  = engine
        self._metrics = metrics
        self._cfg     = config or Config()
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._tasks = [
            asyncio.create_task(
                self._worker_loop(worker_id=i),
                name=f"worker-{i}",
            )
            for i in range(self._cfg.NUM_WORKERS)
        ]
        logger.info("worker pool started", extra={"num_workers": self._cfg.NUM_WORKERS})

    async def stop(self, drain_timeout: float | None = None) -> None:
        """
        Stop gracefully:
          1. Signal workers to stop accepting new jobs
          2. Wait up to drain_timeout for in-flight jobs to finish
          3. Cancel any remaining workers
        """
        self._running = False
        timeout = drain_timeout or self._cfg.DRAIN_TIMEOUT
        logger.info("worker pool stopping", extra={"drain_timeout": timeout})

        try:
            await asyncio.wait_for(self._engine.join(), timeout=timeout)
            logger.info("queue drained — all jobs complete")
        except asyncio.TimeoutError:
            remaining = self._engine.stats()["pending"]
            logger.warning(
                "drain timeout — %d jobs still in queue", remaining,
                extra={"remaining": remaining},
            )
        finally:
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            logger.info("worker pool stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        logger.debug("worker started", extra={"worker_id": worker_id})
        while self._running:
            try:
                job = await self._engine.dequeue()
            except asyncio.CancelledError:
                break

            await self._execute(job, worker_id)

        logger.debug("worker stopped", extra={"worker_id": worker_id})

    async def _execute(self, job: Job, worker_id: int) -> None:
        logger.info(
            "job started",
            extra={"job_id": job.job_id, "func": job.func_name,
                   "attempt": job.attempt, "worker_id": worker_id},
        )
        self._metrics.job_started(job.func_name)

        try:
            result = await asyncio.wait_for(
                job.func(*job.args, **job.kwargs),
                timeout=self._cfg.JOB_TIMEOUT,
            )
            job.result      = result
            job.status      = JobStatus.DONE
            job.finished_at = datetime.now(timezone.utc)
            self._engine.task_done(job)

            self._metrics.job_done(job.func_name, job.duration_ms or 0)
            logger.info(
                "job done",
                extra={"job_id": job.job_id, "func": job.func_name,
                       "duration_ms": job.duration_ms, "worker_id": worker_id},
            )

        except asyncio.TimeoutError:
            job.error = f"Timeout after {self._cfg.JOB_TIMEOUT}s"
            await self._handle_failure(job, worker_id)

        except asyncio.CancelledError:
            # Worker is shutting down mid-job — put job back or accept loss
            job.error = "Worker cancelled"
            self._engine.task_done(job)
            raise

        except Exception as exc:
            job.error = f"{type(exc).__name__}: {exc}"
            await self._handle_failure(job, worker_id)

    async def _handle_failure(self, job: Job, worker_id: int) -> None:
        logger.warning(
            "job failed",
            extra={"job_id": job.job_id, "func": job.func_name,
                   "attempt": job.attempt, "error": job.error, "worker_id": worker_id},
        )
        self._metrics.job_failed(job.func_name)

        policy = RetryPolicy(self._cfg)
        if policy.should_retry(job):
            backoff = policy.backoff_seconds(job)
            logger.info(
                "job retrying",
                extra={"job_id": job.job_id, "func": job.func_name,
                       "attempt": job.attempt + 1, "backoff_s": backoff},
            )
            await self._engine.retry(job, backoff)
        else:
            job.finished_at = datetime.now(timezone.utc)
            self._engine.task_done(job)
            self._engine.send_to_dlq(job)
            self._metrics.job_dlq(job.func_name)
```

---

## 8. Retry & Dead-Letter

```python
# asyncio_queue/retry.py
from __future__ import annotations
import random
from .config import Config
from .models import Job


class RetryPolicy:
    """
    Encapsulates retry decision and backoff calculation.
    Keeps worker.py clean — the policy is swappable.
    """

    def __init__(self, config: Config | None = None):
        self._cfg = config or Config()

    def should_retry(self, job: Job) -> bool:
        return job.attempt < job.max_retries

    def backoff_seconds(self, job: Job) -> float:
        """
        Exponential backoff with optional full jitter.

        Formula (no jitter):  min(base ** attempt, max)
        Formula (jitter):     random(0, min(base ** attempt, max))

        Jitter prevents the "thundering herd" problem when many jobs fail
        simultaneously and all retry at the same instant.
        """
        raw = min(
            self._cfg.BACKOFF_BASE ** (job.attempt + 1),
            self._cfg.BACKOFF_MAX,
        )
        if self._cfg.BACKOFF_JITTER:
            return random.uniform(0, raw)
        return raw


# Example backoff table (base=2, max=60, no jitter):
#   attempt 1  →  2s
#   attempt 2  →  4s
#   attempt 3  →  8s
#   attempt 4  → 16s
#   attempt 5  → 32s
#   attempt 6+ → 60s  (capped)
```

---

## 9. Structured Logging

Structured logs are machine-parseable — essential for Datadog, Loki, CloudWatch.

```python
# asyncio_queue/logging_setup.py
from __future__ import annotations
import json
import logging
import sys
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        # attach any extra= kwargs passed to logger.info()/error()/etc.
        for key, val in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                base[key] = val
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base)


class _PlainFormatter(logging.Formatter):
    FMT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"

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
            return f"{base} | {kv}"
        return base


def setup_logging(level: str = "INFO", json_logs: bool = False) -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter() if json_logs else _PlainFormatter())

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(handler)
```

---

## 10. Metrics

A lightweight in-process counter store. Expose via the health endpoint or a Prometheus scrape.

```python
# asyncio_queue/metrics.py
from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock     # metrics may be read from other threads (e.g. HTTP)


@dataclass
class FunctionMetrics:
    started:   int   = 0
    done:      int   = 0
    failed:    int   = 0
    dlq:       int   = 0
    total_ms:  float = 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.done if self.done else 0.0

    @property
    def error_rate(self) -> float:
        total = self.done + self.failed
        return self.failed / total if total else 0.0


class Metrics:
    """
    Thread-safe in-process metrics store.
    Compatible with Prometheus naming conventions.
    """

    def __init__(self):
        self._lock   = Lock()
        self._funcs: dict[str, FunctionMetrics] = defaultdict(FunctionMetrics)
        self._start  = time.monotonic()

    def _get(self, func_name: str) -> FunctionMetrics:
        return self._funcs[func_name]

    def job_started(self, func_name: str) -> None:
        with self._lock:
            self._get(func_name).started += 1

    def job_done(self, func_name: str, duration_ms: float) -> None:
        with self._lock:
            m = self._get(func_name)
            m.done     += 1
            m.total_ms += duration_ms

    def job_failed(self, func_name: str) -> None:
        with self._lock:
            self._get(func_name).failed += 1

    def job_dlq(self, func_name: str) -> None:
        with self._lock:
            self._get(func_name).dlq += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_s": round(time.monotonic() - self._start, 1),
                "functions": {
                    name: {
                        "started":    m.started,
                        "done":       m.done,
                        "failed":     m.failed,
                        "dlq":        m.dlq,
                        "avg_ms":     round(m.avg_ms, 2),
                        "error_rate": round(m.error_rate, 4),
                    }
                    for name, m in self._funcs.items()
                },
            }

    def prometheus_text(self, engine_stats: dict) -> str:
        """
        Emit metrics in Prometheus text exposition format.
        Scrape with prometheus_client or any Prometheus-compatible agent.
        """
        lines = [
            f'# HELP aq_queue_pending Number of jobs waiting in queue',
            f'# TYPE aq_queue_pending gauge',
            f'aq_queue_pending {engine_stats.get("pending", 0)}',
            f'# HELP aq_queue_running Number of jobs currently executing',
            f'# TYPE aq_queue_running gauge',
            f'aq_queue_running {engine_stats.get("running", 0)}',
            f'# HELP aq_dlq_size Number of jobs in dead-letter queue',
            f'# TYPE aq_dlq_size gauge',
            f'aq_dlq_size {engine_stats.get("dlq_size", 0)}',
        ]
        with self._lock:
            for name, m in self._funcs.items():
                safe = name.replace("-", "_")
                lines += [
                    f'aq_jobs_done_total{{func="{name}"}} {m.done}',
                    f'aq_jobs_failed_total{{func="{name}"}} {m.failed}',
                    f'aq_jobs_dlq_total{{func="{name}"}} {m.dlq}',
                    f'aq_job_duration_ms_sum{{func="{name}"}} {m.total_ms:.2f}',
                ]
        return "\n".join(lines) + "\n"
```

---

## 11. Health-Check HTTP Server

```python
# asyncio_queue/health.py
"""
Tiny HTTP server built on asyncio streams (no extra dependency).
Endpoints:
  GET /health    → {"status": "ok", "stats": {...}}
  GET /metrics   → Prometheus text format
  GET /dlq       → list of dead-letter jobs
"""
from __future__ import annotations
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class HealthServer:
    def __init__(self, engine, metrics, port: int = 8080):
        self._engine  = engine
        self._metrics = metrics
        self._port    = port
        self._server  = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, "0.0.0.0", self._port
        )
        logger.info("health server listening", extra={"port": self._port})

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            raw = await asyncio.wait_for(reader.read(4096), timeout=5)
            first_line = raw.decode(errors="replace").split("\r\n")[0]
            method, path, *_ = (first_line + " ").split(" ", 2)

            if method != "GET":
                await self._respond(writer, 405, "Method Not Allowed", "text/plain")
                return

            if path == "/health" or path == "/":
                body = json.dumps({
                    "status": "ok",
                    "stats": self._engine.stats(),
                }, indent=2)
                await self._respond(writer, 200, body, "application/json")

            elif path == "/metrics":
                body = self._metrics.prometheus_text(self._engine.stats())
                await self._respond(writer, 200, body, "text/plain; version=0.0.4")

            elif path == "/dlq":
                jobs = [j.to_dict() for j in self._engine.dlq_jobs()]
                body = json.dumps(jobs, indent=2)
                await self._respond(writer, 200, body, "application/json")

            else:
                await self._respond(writer, 404, "Not Found", "text/plain")

        except Exception as exc:
            logger.warning("health handler error: %s", exc)
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    async def _respond(
        writer: asyncio.StreamWriter, status: int, body: str, content_type: str
    ) -> None:
        payload = body.encode()
        response = (
            f"HTTP/1.1 {status} \r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode() + payload
        writer.write(response)
        await writer.drain()
```

---

## 12. Graceful Shutdown

```python
# asyncio_queue/shutdown.py
from __future__ import annotations
import asyncio
import logging
import signal
from typing import Callable

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Installs SIGINT and SIGTERM handlers that trigger an ordered shutdown:
      1. Stop accepting new jobs (producer side)
      2. Drain in-flight jobs (up to drain_timeout)
      3. Cancel remaining workers
      4. Stop health server
      5. Exit cleanly

    Usage:
        shutdown = GracefulShutdown(on_shutdown=engine.stop)
        shutdown.install()
        await shutdown.wait()   # blocks until signal received
    """

    def __init__(self, on_shutdown: Callable[[], None]):
        self._on_shutdown = on_shutdown
        self._event       = asyncio.Event()

    def install(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._trigger)
        logger.debug("graceful shutdown handlers installed")

    def _trigger(self) -> None:
        logger.info("shutdown signal received — draining queue...")
        self._event.set()
        self._on_shutdown()

    async def wait(self) -> None:
        await self._event.wait()
```

---

## 13. Putting It All Together — `engine.py`

```python
# asyncio_queue/engine.py
"""
Public API — the only file application code should import from.

Usage:
    from asyncio_queue.engine import AsyncQueue

    queue = AsyncQueue()

    @queue.task
    async def send_email(to: str, subject: str):
        ...

    async def main():
        await queue.start()
        job = await queue.send("send_email", to="a@b.com", subject="Hi")
        await queue.join()
        await queue.stop()
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any, Awaitable, Callable

from .config import Config
from .health import HealthServer
from .logging_setup import setup_logging
from .metrics import Metrics
from .models import Job
from .queue_engine import QueueEngine
from .shutdown import GracefulShutdown
from .worker import WorkerPool
from . import registry as _registry

logger = logging.getLogger(__name__)


class AsyncQueue:
    def __init__(self, config: Config | None = None):
        self._cfg     = config or Config()
        self._engine  = QueueEngine(self._cfg)
        self._metrics = Metrics()
        self._pool    = WorkerPool(self._engine, self._metrics, self._cfg)
        self._health  = (
            HealthServer(self._engine, self._metrics, self._cfg.HEALTH_PORT)
            if self._cfg.HEALTH_ENABLED else None
        )
        self._shutdown = GracefulShutdown(on_shutdown=self._trigger_stop)
        self._stop_event = asyncio.Event()

    # ── Decorator for registering tasks ──────────────────────────────────

    def task(
        self,
        func: Callable[..., Awaitable] | None = None,
        *,
        name: str | None = None,
    ):
        """
        Decorator to register a function with the queue.

            @queue.task
            async def process_order(order_id: int): ...

            @queue.task(name="my_task")
            async def process_order(order_id: int): ...
        """
        return _registry.register(func, name=name)

    # ── Enqueue ───────────────────────────────────────────────────────────

    async def send(
        self,
        func_name: str,
        *args: Any,
        priority: int = 5,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> Job:
        return await self._engine.enqueue(
            func_name, *args, priority=priority,
            max_retries=max_retries, **kwargs
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        setup_logging(self._cfg.LOG_LEVEL, self._cfg.LOG_JSON)
        logger.info("AsyncQueue starting", extra={"config": {
            "workers": self._cfg.NUM_WORKERS,
            "maxsize": self._cfg.QUEUE_MAXSIZE,
            "priority": self._cfg.USE_PRIORITY,
        }})
        if self._health:
            await self._health.start()
        await self._pool.start()
        self._shutdown.install()

    async def stop(self) -> None:
        await self._pool.stop(self._cfg.DRAIN_TIMEOUT)
        if self._health:
            await self._health.stop()
        logger.info("AsyncQueue stopped")

    async def join(self) -> None:
        """Wait until all currently enqueued jobs have finished."""
        await self._engine.join()

    async def run_forever(self) -> None:
        """Start and block until a shutdown signal is received."""
        await self.start()
        await self._stop_event.wait()
        await self.stop()

    def _trigger_stop(self) -> None:
        self._stop_event.set()

    # ── Inspection ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {**self._engine.stats(), **self._metrics.snapshot()}

    def get_job(self, job_id: str) -> Job | None:
        return self._engine.get_job(job_id)

    def dlq(self) -> list[Job]:
        return self._engine.dlq_jobs()
```

---

## 14. Sample Tasks

```python
# asyncio_queue/example_tasks.py
import asyncio
import random
from .engine import AsyncQueue

# Note: tasks are registered against a shared queue instance.
# In production, import your single queue instance from a module.

def register_example_tasks(queue: AsyncQueue) -> None:

    @queue.task
    async def send_email(to: str, subject: str, body: str = "") -> str:
        await asyncio.sleep(0.05)   # simulate SMTP I/O
        return f"sent:{to}"

    @queue.task
    async def process_payment(user_id: int, amount_cents: int) -> dict:
        if amount_cents <= 0:
            raise ValueError("amount_cents must be positive")
        if amount_cents > 100_000_00:   # $100,000 limit
            raise ValueError(f"Amount {amount_cents} exceeds limit")
        await asyncio.sleep(0.1)        # simulate payment API
        return {"user_id": user_id, "charged": amount_cents, "currency": "USD"}

    @queue.task
    async def resize_image(path: str, width: int, height: int) -> str:
        await asyncio.sleep(0.2)        # simulate image processing
        return f"resized:{path}:{width}x{height}"

    @queue.task
    async def flaky_task(fail_rate: float = 0.5) -> str:
        """For testing retry logic."""
        if random.random() < fail_rate:
            raise RuntimeError("Flaky task failed (expected)")
        return "flaky_task:ok"
```

---

## 15. Main Entry Point

```python
# asyncio_queue/main.py
import asyncio
import os
from .engine import AsyncQueue
from .example_tasks import register_example_tasks

async def main():
    queue = AsyncQueue()
    register_example_tasks(queue)
    await queue.start()

    # --- enqueue work ---
    jobs = []
    for i in range(5):
        j = await queue.send("send_email",
                             to=f"user{i}@example.com",
                             subject=f"Hello #{i}")
        jobs.append(j)

    j = await queue.send("process_payment", user_id=42, amount_cents=4999)
    jobs.append(j)

    j = await queue.send("flaky_task", fail_rate=0.8, max_retries=4)
    jobs.append(j)

    # --- wait for all to complete ---
    await queue.join()

    # --- report results ---
    print("\n── Job Results ──────────────────────────────────")
    for job in jobs:
        result = queue.get_job(job.job_id)
        status = result.status.value if result else "unknown"
        value  = result.result or result.error if result else "?"
        print(f"  [{status:8}] {job.func_name}({job.job_id[:8]}) → {value}")

    dlq = queue.dlq()
    if dlq:
        print(f"\n── Dead Letter Queue ({len(dlq)} jobs) ──")
        for j in dlq:
            print(f"  {j.func_name}[{j.job_id[:8]}]: {j.error}")

    print("\n── Stats ──")
    import json
    print(json.dumps(queue.stats(), indent=2))

    await queue.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 16. Tests

```python
# asyncio_queue/tests/test_models.py
import pytest
from asyncio_queue.models import Job, JobStatus

def test_job_defaults():
    job = Job(func_name="send_email")
    assert job.status == JobStatus.PENDING
    assert job.attempt == 0
    assert job.job_id  != ""

def test_job_lt_compares_priority():
    low  = Job(func_name="f", priority=10)
    high = Job(func_name="f", priority=1)
    assert high < low

def test_duration_ms_none_before_run():
    job = Job(func_name="f")
    assert job.duration_ms is None

def test_to_dict():
    job = Job(func_name="send_email", priority=3)
    d = job.to_dict()
    assert d["func_name"] == "send_email"
    assert d["status"] == "pending"
    assert "job_id" in d
```

```python
# asyncio_queue/tests/test_retry.py
from asyncio_queue.retry import RetryPolicy
from asyncio_queue.models import Job
from asyncio_queue.config import Config

def make_job(attempt: int = 0, max_retries: int = 3) -> Job:
    j = Job(func_name="f")
    j.attempt     = attempt
    j.max_retries = max_retries
    return j

def test_should_retry_within_limit():
    policy = RetryPolicy()
    assert policy.should_retry(make_job(attempt=0)) is True
    assert policy.should_retry(make_job(attempt=2)) is True

def test_should_not_retry_at_limit():
    policy = RetryPolicy()
    assert policy.should_retry(make_job(attempt=3)) is False

def test_backoff_increases():
    cfg = Config()
    cfg.BACKOFF_JITTER = False
    policy = RetryPolicy(cfg)
    b1 = policy.backoff_seconds(make_job(attempt=0))
    b2 = policy.backoff_seconds(make_job(attempt=1))
    b3 = policy.backoff_seconds(make_job(attempt=2))
    assert b1 < b2 < b3

def test_backoff_capped():
    cfg = Config()
    cfg.BACKOFF_MAX    = 10.0
    cfg.BACKOFF_JITTER = False
    policy = RetryPolicy(cfg)
    b = policy.backoff_seconds(make_job(attempt=100))
    assert b <= 10.0
```

```python
# asyncio_queue/tests/test_integration.py
import asyncio
import pytest
from asyncio_queue.engine import AsyncQueue
from asyncio_queue.config import Config

@pytest.fixture
def cfg():
    c = Config()
    c.NUM_WORKERS    = 2
    c.QUEUE_MAXSIZE  = 50
    c.JOB_TIMEOUT    = 2.0
    c.HEALTH_ENABLED = False   # don't bind a port in tests
    c.MAX_RETRIES    = 2
    c.BACKOFF_BASE   = 0.01    # very fast retries in tests
    c.BACKOFF_JITTER = False
    return c

@pytest.fixture
async def queue(cfg):
    q = AsyncQueue(config=cfg)

    @q.task
    async def add(a: int, b: int) -> int:
        return a + b

    @q.task
    async def always_fail() -> None:
        raise RuntimeError("always fails")

    @q.task
    async def slow_task(seconds: float) -> str:
        await asyncio.sleep(seconds)
        return "done"

    await q.start()
    yield q
    await q.stop()


@pytest.mark.asyncio
async def test_successful_job(queue):
    job = await queue.send("add", 3, 4)
    await queue.join()
    result = queue.get_job(job.job_id)
    assert result.status.value == "done"
    assert result.result == 7

@pytest.mark.asyncio
async def test_failed_job_goes_to_dlq(queue):
    job = await queue.send("always_fail")
    await queue.join()
    dlq = queue.dlq()
    ids = [j.job_id for j in dlq]
    assert job.job_id in ids

@pytest.mark.asyncio
async def test_job_timeout_retries_then_dlq(queue):
    # slow_task takes 5s, timeout is 2s → will timeout, retry 2x, then DLQ
    job = await queue.send("slow_task", 5.0)
    await asyncio.wait_for(queue.join(), timeout=30)
    dlq = queue.dlq()
    ids = [j.job_id for j in dlq]
    assert job.job_id in ids

@pytest.mark.asyncio
async def test_stats_tracks_counts(queue):
    for _ in range(4):
        await queue.send("add", 1, 2)
    await queue.join()
    stats = queue.stats()
    assert stats["by_status"].get("done", 0) == 4

@pytest.mark.asyncio
async def test_enqueue_unknown_function_raises(queue):
    with pytest.raises(ValueError, match="not registered"):
        await queue.send("nonexistent_function")

@pytest.mark.asyncio
async def test_multiple_concurrent_jobs(queue):
    jobs = [await queue.send("add", i, i) for i in range(20)]
    await queue.join()
    for job in jobs:
        result = queue.get_job(job.job_id)
        assert result.status.value == "done"
```

```python
# asyncio_queue/tests/conftest.py
import pytest

# enable pytest-asyncio auto mode
pytest_plugins = ("pytest_asyncio",)
```

---

## 17. Running the Project

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install pytest pytest-asyncio
```

### Run the example

```bash
python -m asyncio_queue.main
```

### Run tests

```bash
pytest asyncio_queue/tests/ -v
```

### Configure via environment

```bash
AQ_NUM_WORKERS=8 \
AQ_MAXSIZE=5000 \
AQ_JOB_TIMEOUT=120 \
AQ_MAX_RETRIES=5 \
AQ_LOG_JSON=true \
AQ_HEALTH_PORT=9090 \
python -m asyncio_queue.main
```

### Check health endpoint

```bash
# start in background
python -m asyncio_queue.main &

curl http://localhost:8080/health     # → JSON stats
curl http://localhost:8080/metrics    # → Prometheus text
curl http://localhost:8080/dlq        # → dead-letter jobs
```

---

## 18. Production Checklist

| Concern | Solution in this project |
|---|---|
| Backpressure | `maxsize` on `asyncio.Queue` — producers block when full |
| Duplicate execution | Single-process, no distributed concern |
| Job loss on crash | ❌ — in-memory only. See `02-arq-queue.md` |
| Observability | Structured JSON logs + Prometheus metrics endpoint |
| Graceful shutdown | SIGINT/SIGTERM handler with configurable drain timeout |
| Retry storms | Exponential backoff with full jitter |
| Infinite loops | Per-job `max_retries` + DLQ |
| Misconfigured functions | Registry validates at `enqueue()` time, not at run time |
| Test coverage | Unit + integration tests with `pytest-asyncio` |
| Configuration | All tunables via env vars — no hardcoded values |
| Resource limits | `NUM_WORKERS` and `QUEUE_MAXSIZE` prevent runaway memory |

---

## 20. `asyncio.TaskGroup` Worker Pattern (Python 3.11+)

The `TaskGroup`-based worker is safer than the classic `create_task` approach
because it cancels all workers and propagates exceptions cleanly.

```python
# asyncio_queue/worker_taskgroup.py
"""Alternative WorkerPool using TaskGroup (Python 3.11+)."""
from __future__ import annotations
import asyncio
import logging

from .config import Config
from .models import Job, JobStatus
from .queue_engine import QueueEngine
from .retry import RetryPolicy
from .metrics import Metrics

logger = logging.getLogger(__name__)


class TaskGroupWorkerPool:
    """
    Uses asyncio.TaskGroup for structured concurrency.
    All workers are launched as tasks in the group.
    If any worker crashes (unexpected exception), all siblings are cancelled.
    """

    def __init__(self, engine: QueueEngine, metrics: Metrics, config: Config | None = None):
        self._engine  = engine
        self._metrics = metrics
        self._cfg     = config or Config()
        self._stop    = asyncio.Event()

    async def run(self) -> None:
        """Start NUM_WORKERS workers, all inside one TaskGroup."""
        try:
            async with asyncio.TaskGroup() as tg:
                for i in range(self._cfg.NUM_WORKERS):
                    tg.create_task(
                        self._worker_loop(worker_id=i),
                        name=f"worker-{i}",
                    )
        except* Exception as eg:
            # ExceptionGroup: collect all worker failures
            for exc in eg.exceptions:
                logger.error("worker failed: %s", exc)

    def stop(self) -> None:
        self._stop.set()

    async def _worker_loop(self, worker_id: int) -> None:
        while not self._stop.is_set():
            try:
                # Use wait with timeout so stop event is checked periodically
                async with asyncio.timeout(1.0):
                    job = await self._engine.dequeue()
                await self._execute(job, worker_id)
            except asyncio.TimeoutError:
                continue   # check _stop and loop
            except asyncio.CancelledError:
                break

    async def _execute(self, job: Job, worker_id: int) -> None:
        self._metrics.job_started(job.func_name)
        try:
            result = await asyncio.wait_for(
                job.func(*job.args, **job.kwargs),
                timeout=self._cfg.JOB_TIMEOUT,
            )
            job.result = result
            job.status = JobStatus.DONE
            self._engine.task_done(job)
            self._metrics.job_done(job.func_name, 0)
        except Exception as exc:
            job.error = str(exc)
            policy = RetryPolicy(self._cfg)
            if policy.should_retry(job):
                await self._engine.retry(job, policy.backoff_seconds(job))
            else:
                self._engine.task_done(job)
                self._engine.send_to_dlq(job)
            self._metrics.job_failed(job.func_name)
```

---

## 21. `contextvars` — Tracing Job Context Across Coroutines

`contextvars` lets you attach a job ID to all log lines produced by a coroutine,
without threading it through every function call.

```python
# asyncio_queue/context.py
import contextvars
import logging
from contextlib import contextmanager

# Module-level context variable
job_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "job_id", default="<no-job>"
)
func_name_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "func_name", default=""
)


class ContextFilter(logging.Filter):
    """Inject context variables into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id   = job_id_var.get()
        record.func_name_ctx = func_name_var.get()
        return True


def set_job_context(job_id: str, func_name: str) -> contextvars.Token:
    """Set job context; returns token to restore previous context."""
    t1 = job_id_var.set(job_id)
    t2 = func_name_var.set(func_name)
    return t1  # for simplicity, only return first token (could be a tuple)


def clear_job_context(token: contextvars.Token) -> None:
    job_id_var.reset(token)


# Usage in worker._execute():
async def _execute(self, job: Job, worker_id: int) -> None:
    token = set_job_context(job.job_id, job.func_name)
    try:
        # All log calls inside job.func will automatically include job_id
        logger.info("job_started")   # logged with job_id in context
        result = await job.func(*job.args, **job.kwargs)
        logger.info("job_done", extra={"result": result})
    finally:
        clear_job_context(token)
```

---

## 19. Limitations & When to Graduate

`asyncio.Queue` lives entirely **in memory** in **one process**.

| You need this | Graduate to |
|---|---|
| Jobs survive process restart | `02-arq-queue.md` (Redis) |
| Workers on multiple machines | `02-arq-queue.md` (Redis) |
| Query jobs with SQL | `03-postgresql-queue.md` |
| > 10k jobs/sec sustained | Redis (arq) or Kafka/Faust |
| Scheduled / cron jobs | arq or PostgreSQL queue |
| Job visibility dashboard | arq + RQ Dashboard / Flower |

> **Rule:** Use `asyncio.Queue` when all job processing fits inside one Python process
> (e.g., a FastAPI background worker, a data pipeline stage, a WebSocket message processor).
