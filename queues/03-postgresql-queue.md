# Building a PostgreSQL-Backed Async Queue from Scratch

> **Level:** Intermediate → Advanced  
> **Dependencies:** `asyncpg`, `sqlalchemy[asyncio]` (optional), `python-ulid` (optional)  
> **Goal:** Build a persistent, crash-safe async job queue using only PostgreSQL — no Redis required

---

## Table of Contents

1. [Why PostgreSQL for a Queue?](#1-why-postgresql-for-a-queue)
2. [The Key: `SELECT ... FOR UPDATE SKIP LOCKED`](#2-the-key-select--for-update-skip-locked)
3. [Architecture Overview](#3-architecture-overview)
4. [Setup](#4-setup)
5. [Step 1 — Schema Design](#step-1--schema-design)
6. [Step 2 — Database Connection Pool](#step-2--database-connection-pool)
7. [Step 3 — Enqueue a Job](#step-3--enqueue-a-job)
8. [Step 4 — Dequeue a Job (atomic claim)](#step-4--dequeue-a-job-atomic-claim)
9. [Step 5 — Worker Loop](#step-5--worker-loop)
10. [Step 6 — Result Storage & Status Updates](#step-6--result-storage--status-updates)
11. [Step 7 — Retries & Backoff](#step-7--retries--backoff)
12. [Step 8 — Delayed / Scheduled Jobs](#step-8--delayed--scheduled-jobs)
13. [Step 9 — LISTEN / NOTIFY (no polling)](#step-9--listen--notify-no-polling)
14. [Step 10 — Dead Letter Queue](#step-10--dead-letter-queue)
15. [Step 11 — Full Implementation](#step-11--full-implementation)
16. [Project Layout](#project-layout)

---

## 1. Why PostgreSQL for a Queue?

| Concern | PostgreSQL Queue |
|---|---|
| No extra infrastructure | ✅ You already have Postgres |
| ACID guarantees | ✅ Jobs never lost on crash |
| Complex queries on jobs | ✅ Full SQL — filter, sort, aggregate |
| Audit trail / history | ✅ Store results, errors, durations forever |
| Distributed workers | ✅ SKIP LOCKED handles concurrent dequeue safely |
| Delayed jobs | ✅ `run_at` column + WHERE clause |
| Dashboard | ✅ Any SQL client, Grafana, etc |
| Scale | ⚠️ 100s–1000s jobs/sec (not millions — use Redis for that) |

---

## 2. The Key: `SELECT ... FOR UPDATE SKIP LOCKED`

This is the entire foundation of a PostgreSQL queue.

### The Problem Without It

```sql
-- Worker 1 reads job #1
SELECT * FROM jobs WHERE status = 'pending' LIMIT 1;

-- Worker 2 reads the SAME job #1 before W1 updates it
SELECT * FROM jobs WHERE status = 'pending' LIMIT 1;

-- Both workers run the same job → DUPLICATE EXECUTION 🚨
```

### The Solution

```sql
BEGIN;
  SELECT id, func_name, args
  FROM jobs
  WHERE status = 'pending'
    AND run_at <= NOW()
  ORDER BY priority ASC, created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;      -- ← magic line
COMMIT;
```

What `FOR UPDATE SKIP LOCKED` does:
- `FOR UPDATE` → locks the selected row
- `SKIP LOCKED` → if a row is already locked by another worker, **skip it** and pick the next one
- Result: each worker atomically claims a **different** job, **no duplicates**

---

## 3. Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                       PRODUCER                             │
│   enqueue(func, *args)                                     │
│       → INSERT INTO jobs (status='pending', ...)           │
│       → NOTIFY job_available                               │
└──────────────────────┬─────────────────────────────────────┘
                       │  PostgreSQL
┌──────────────────────▼─────────────────────────────────────┐
│                    jobs TABLE                              │
│  id | func_name | args | status | priority | run_at | ...  │
│  ───────────────────────────────────────────────────────── │
│  1  | send_email | ...  | done   | 5        | ...    | ... │
│  2  | send_sms   | ...  | running| 1        | ...    | ... │
│  3  | gen_report | ...  | pending| 5        | +10s   | ... │
└──────────────────────┬─────────────────────────────────────┘
          SKIP LOCKED  │
   ┌───────────────────┼───────────────────┐
   ▼                   ▼                   ▼
Worker-1           Worker-2           Worker-3
claim job          claim job          claim job
update status      update status      update status
run func()         run func()         run func()
save result        save result        save result
```

---

## 4. Setup

```bash
pip install asyncpg

# PostgreSQL via Docker
docker run -d \
  --name pgqueue \
  -e POSTGRES_DB=queuedb \
  -e POSTGRES_USER=queueuser \
  -e POSTGRES_PASSWORD=secret \
  -p 5432:5432 \
  postgres:16-alpine
```

```python
# DSN
DATABASE_URL = "postgresql://queueuser:secret@localhost:5432/queuedb"
```

---

## Step 1 — Schema Design

```python
# pgqueue/schema.py

CREATE_SCHEMA = """
-- Main jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id              BIGSERIAL PRIMARY KEY,
    job_id          TEXT NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,
    queue           TEXT NOT NULL DEFAULT 'default',
    func_name       TEXT NOT NULL,
    args            JSONB NOT NULL DEFAULT '[]',
    kwargs          JSONB NOT NULL DEFAULT '{}',

    -- lifecycle
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','done','failed','retrying','cancelled')),
    priority        INT  NOT NULL DEFAULT 5,     -- lower = higher priority
    attempt         INT  NOT NULL DEFAULT 0,
    max_retries     INT  NOT NULL DEFAULT 3,

    -- timing
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- for delayed jobs
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,

    -- output
    result          JSONB,
    error           TEXT,
    worker_id       TEXT,

    -- heartbeat (detect stuck jobs)
    heartbeat_at    TIMESTAMPTZ
);

-- Indexes for the dequeue query (critical for performance)
CREATE INDEX IF NOT EXISTS idx_jobs_dequeue ON jobs (queue, priority ASC, created_at ASC)
    WHERE status IN ('pending', 'retrying') AND run_at <= NOW();

CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON jobs (run_at)
    WHERE status = 'pending' AND run_at > NOW();

CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs (job_id);

-- Dead letter table (failed jobs archive)
CREATE TABLE IF NOT EXISTS jobs_dlq (
    LIKE jobs INCLUDING ALL,
    moved_to_dlq_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

DROP_SCHEMA = """
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS jobs_dlq CASCADE;
"""
```

---

## Step 2 — Database Connection Pool

```python
# pgqueue/db.py
import asyncpg

_pool: asyncpg.Pool | None = None

async def get_pool(dsn: str, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=min_size,
            max_size=max_size,
            command_timeout=30,
        )
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def init_schema(pool: asyncpg.Pool):
    from .schema import CREATE_SCHEMA
    async with pool.acquire() as conn:
        await conn.execute(CREATE_SCHEMA)
    print("✅ Schema initialized")
```

---

## Step 3 — Enqueue a Job

```python
# pgqueue/enqueue.py
import json
import asyncpg
from datetime import datetime, timedelta, timezone

async def enqueue(
    pool: asyncpg.Pool,
    func_name: str,
    *args,
    kwargs: dict = None,
    queue: str = "default",
    priority: int = 5,
    max_retries: int = 3,
    delay_seconds: float = 0,
    run_at: datetime | None = None,
) -> str:
    """Insert a job and return its job_id."""
    kwargs = kwargs or {}

    if run_at is None:
        run_at = datetime.now(timezone.utc)
    if delay_seconds:
        run_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO jobs (func_name, args, kwargs, queue, priority, max_retries, run_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4, $5, $6, $7)
            RETURNING job_id
            """,
            func_name,
            json.dumps(list(args)),
            json.dumps(kwargs),
            queue,
            priority,
            max_retries,
            run_at,
        )

    job_id = row["job_id"]
    print(f"📥 Enqueued {func_name}[{job_id[:8]}] → queue:{queue}")
    return job_id
```

---

## Step 4 — Dequeue a Job (atomic claim)

This is the most important function — atomically claim one job:

```python
# pgqueue/dequeue.py
import asyncpg
from datetime import datetime, timezone

DEQUEUE_SQL = """
WITH claimed AS (
    SELECT id
    FROM jobs
    WHERE queue    = $1
      AND status   IN ('pending', 'retrying')
      AND run_at   <= NOW()
    ORDER BY priority ASC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED        -- ← atomic claim, no duplicates
)
UPDATE jobs
SET
    status      = 'running',
    started_at  = NOW(),
    worker_id   = $2,
    heartbeat_at = NOW()
WHERE id = (SELECT id FROM claimed)
RETURNING
    id, job_id, func_name, args, kwargs,
    attempt, max_retries, queue, priority;
"""

async def dequeue(
    pool: asyncpg.Pool,
    queue: str = "default",
    worker_id: str = "worker-1",
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DEQUEUE_SQL, queue, worker_id)

    if row is None:
        return None

    return {
        "id":          row["id"],
        "job_id":      row["job_id"],
        "func_name":   row["func_name"],
        "args":        row["args"],       # already parsed from JSONB
        "kwargs":      row["kwargs"],
        "attempt":     row["attempt"],
        "max_retries": row["max_retries"],
        "queue":       row["queue"],
    }
```

> **Why this is safe:**  
> The `WITH claimed AS (...)` + `UPDATE` happens in a single statement.  
> `SKIP LOCKED` ensures two workers never claim the same row.  
> Even if a worker crashes after claiming, we can detect it via `heartbeat_at`.

---

## Step 5 — Worker Loop

```python
# pgqueue/worker.py
import asyncio
import asyncpg
import socket
import time
from typing import Callable, Awaitable
from .dequeue import dequeue
from .results import mark_done, mark_failed, update_heartbeat

class PGWorker:
    def __init__(
        self,
        pool: asyncpg.Pool,
        functions: dict[str, Callable[..., Awaitable]],
        queue: str = "default",
        concurrency: int = 5,
        poll_interval: float = 1.0,
        job_timeout: float = 300.0,
    ):
        self.pool = pool
        self.functions = functions
        self.queue = queue
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self.job_timeout = job_timeout
        self.worker_id = f"{socket.gethostname()}-{id(self)}"
        self._semaphore = asyncio.Semaphore(concurrency)
        self._running = True

    async def run(self):
        print(f"🚀 PGWorker '{self.worker_id}' started on queue '{self.queue}'")

        # heartbeat updater runs in background
        asyncio.create_task(self._heartbeat_loop())

        while self._running:
            # don't dequeue if already at max concurrency
            if self._semaphore._value == 0:
                await asyncio.sleep(0.1)
                continue

            job = await dequeue(self.pool, self.queue, self.worker_id)

            if job is None:
                # queue is empty — wait before polling again
                await asyncio.sleep(self.poll_interval)
                continue

            # process job in background
            asyncio.create_task(self._handle_job(job))

    async def _handle_job(self, job: dict):
        async with self._semaphore:
            job_id    = job["job_id"]
            func_name = job["func_name"]
            func      = self.functions.get(func_name)

            if func is None:
                await mark_failed(self.pool, job_id, f"Unknown function: {func_name}")
                return

            print(f"  ▶️  {func_name}[{job_id[:8]}] attempt={job['attempt']}")
            try:
                result = await asyncio.wait_for(
                    func(*job["args"], **job["kwargs"]),
                    timeout=self.job_timeout,
                )
                await mark_done(self.pool, job_id, result)
                print(f"  ✅ {func_name}[{job_id[:8]}] done")

            except asyncio.TimeoutError:
                await self._handle_failure(job, "TimeoutError")

            except Exception as e:
                await self._handle_failure(job, str(e))

    async def _handle_failure(self, job: dict, error: str):
        job_id    = job["job_id"]
        attempt   = job["attempt"]
        max_retries = job["max_retries"]

        if attempt < max_retries:
            backoff = 2 ** (attempt + 1)   # 2s, 4s, 8s...
            next_run_at = time.time() + backoff
            print(f"  🔁 {job['func_name']}[{job_id[:8]}] retry {attempt+1}/{max_retries} in {backoff}s")
            await schedule_retry(self.pool, job_id, attempt + 1, next_run_at, error)
        else:
            print(f"  💀 {job['func_name']}[{job_id[:8]}] → DLQ")
            await move_to_dlq(self.pool, job_id, error)

    async def _heartbeat_loop(self):
        """Update heartbeat every 10s so we can detect stuck workers."""
        while self._running:
            await update_heartbeat(self.pool, self.worker_id, self.queue)
            await asyncio.sleep(10)

    def stop(self):
        self._running = False
```

---

## Step 6 — Result Storage & Status Updates

```python
# pgqueue/results.py
import asyncpg
import json
from datetime import datetime, timezone

async def mark_done(pool: asyncpg.Pool, job_id: str, result: any):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE jobs
            SET status      = 'done',
                result      = $2::jsonb,
                finished_at = NOW()
            WHERE job_id = $1
            """,
            job_id,
            json.dumps({"value": str(result)}),
        )

async def mark_failed(pool: asyncpg.Pool, job_id: str, error: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE jobs
            SET status      = 'failed',
                error       = $2,
                finished_at = NOW()
            WHERE job_id = $1
            """,
            job_id, error,
        )

async def schedule_retry(
    pool: asyncpg.Pool, job_id: str, new_attempt: int, run_at_ts: float, error: str
):
    from datetime import datetime, timezone
    run_at = datetime.fromtimestamp(run_at_ts, tz=timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE jobs
            SET status   = 'retrying',
                attempt  = $2,
                run_at   = $3,
                error    = $4
            WHERE job_id = $1
            """,
            job_id, new_attempt, run_at, error,
        )

async def move_to_dlq(pool: asyncpg.Pool, job_id: str, error: str):
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO jobs_dlq
                SELECT *, NOW() FROM jobs WHERE job_id = $1
                """,
                job_id,
            )
            await conn.execute(
                """
                UPDATE jobs SET status = 'failed', error = $2 WHERE job_id = $1
                """,
                job_id, error,
            )

async def update_heartbeat(pool: asyncpg.Pool, worker_id: str, queue: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE jobs SET heartbeat_at = NOW()
            WHERE worker_id = $1 AND status = 'running'
            """,
            worker_id,
        )

async def get_result(pool: asyncpg.Pool, job_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT job_id, status, result, error, started_at, finished_at FROM jobs WHERE job_id = $1",
            job_id,
        )
    if row is None:
        return None
    return dict(row)

async def wait_for_result(pool: asyncpg.Pool, job_id: str, timeout: float = 30) -> dict:
    import asyncio
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        row = await get_result(pool, job_id)
        if row and row["status"] in ("done", "failed"):
            return row
        await asyncio.sleep(0.3)
    raise TimeoutError(f"Job {job_id} did not complete in {timeout}s")
```

---

## Step 7 — Retries & Backoff

Already wired into the worker. Summary of the retry SQL:

```sql
-- Schedule a retry
UPDATE jobs
SET
    status  = 'retrying',
    attempt = $new_attempt,
    run_at  = NOW() + INTERVAL '$backoff seconds',
    error   = $last_error
WHERE job_id = $1;

-- The worker will pick it up again once run_at <= NOW()
```

---

## Step 8 — Delayed / Scheduled Jobs

Delayed jobs just use the `run_at` column — no separate table needed:

```python
# delay_seconds=10 → run_at = NOW() + 10s
await enqueue(pool, "send_reminder", user_id=42, delay_seconds=10)

# specific time
from datetime import datetime, timezone
run_at = datetime(2025, 12, 25, 9, 0, 0, tzinfo=timezone.utc)
await enqueue(pool, "send_xmas_email", run_at=run_at)
```

The dequeue query already filters: `AND run_at <= NOW()` — delayed jobs are invisible until ready.

### Cron-style Recurring Jobs

```python
# pgqueue/cron.py
import asyncio
import asyncpg
from croniter import croniter
from datetime import datetime, timezone

CRON_JOBS = [
    {"func_name": "cleanup_old_jobs",  "cron": "0 * * * *"},   # hourly
    {"func_name": "send_daily_digest", "cron": "0 9 * * *"},   # 9am daily
]

async def cron_scheduler(pool: asyncpg.Pool):
    while True:
        now = datetime.now(timezone.utc)
        for job_def in CRON_JOBS:
            cron = croniter(job_def["cron"], now)
            next_run = cron.get_next(datetime)
            # Enqueue 1 second before the scheduled time
            delay = (next_run - now).total_seconds()
            if 0 <= delay <= 60:
                await enqueue(pool, job_def["func_name"], run_at=next_run)
        await asyncio.sleep(60)  # check every minute
```

> Install: `pip install croniter`

---

## Step 9 — LISTEN / NOTIFY (no polling)

Replace the `poll_interval` sleep with PostgreSQL's push notification:

```python
# pgqueue/notify.py
import asyncpg
import asyncio

CHANNEL = "job_available"

# ── Producer side: notify after insert ──────────────────────
async def enqueue_with_notify(pool, func_name, *args, queue="default", **kwargs):
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "INSERT INTO jobs (func_name, args, kwargs, queue) VALUES ($1,$2::jsonb,$3::jsonb,$4) RETURNING job_id",
                func_name, str(list(args)), str(kwargs), queue,
            )
            # notify all listening workers
            await conn.execute(f"NOTIFY {CHANNEL}, '{queue}'")
    return row["job_id"]

# ── Worker side: listen instead of polling ──────────────────
async def listen_for_jobs(pool: asyncpg.Pool, on_job_available):
    conn = await pool.acquire()
    await conn.add_listener(CHANNEL, lambda *_: asyncio.ensure_future(on_job_available()))
    print(f"👂 Listening on channel '{CHANNEL}'")
    try:
        while True:
            await asyncio.sleep(3600)   # keep alive; notifications are push
    finally:
        await pool.release(conn)
```

Workers receive instant notification instead of polling every second:

```
Producer               PostgreSQL             Worker
  │                        │                    │
  ├─ INSERT job ──────────►│                    │
  ├─ NOTIFY job_available ►│                    │
  │                        ├─ LISTEN notify ───►│
  │                        │◄── notification ───┤
  │                        │                    ├─ dequeue()
  │                        │                    ├─ run job
```

---

## Step 10 — Dead Letter Queue

```python
# pgqueue/dlq.py
import asyncpg

async def list_dlq(pool: asyncpg.Pool, limit: int = 50) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT job_id, func_name, error, moved_to_dlq_at FROM jobs_dlq ORDER BY moved_to_dlq_at DESC LIMIT $1",
            limit,
        )
    return [dict(row) for row in rows]

async def retry_dlq_job(pool: asyncpg.Pool, job_id: str):
    """Move a single DLQ job back to pending."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO jobs
                SELECT id, job_id, queue, func_name, args, kwargs, 'pending',
                       priority, 0, max_retries, NOW(), NOW(), NULL, NULL,
                       NULL, NULL, NULL, NULL
                FROM jobs_dlq WHERE job_id = $1
                ON CONFLICT (job_id) DO UPDATE
                SET status='pending', attempt=0, run_at=NOW()
                """,
                job_id,
            )
            await conn.execute("DELETE FROM jobs_dlq WHERE job_id = $1", job_id)

async def retry_all_dlq(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT job_id FROM jobs_dlq")
    for row in rows:
        await retry_dlq_job(pool, row["job_id"])
    print(f"♻️  Moved {len(rows)} DLQ jobs back to queue")
```

---

## Step 11 — Full Implementation

```python
# pgqueue/main.py
import asyncio
from .db import get_pool, init_schema, close_pool
from .enqueue import enqueue
from .worker import PGWorker
from .results import wait_for_result, get_result
from .dlq import list_dlq

DATABASE_URL = "postgresql://queueuser:secret@localhost:5432/queuedb"

# ── Define your async functions ──────────────────────────────
async def send_email(to: str, subject: str):
    await asyncio.sleep(0.1)
    print(f"    📧 Email → {to}: {subject}")
    return f"sent:{to}"

async def process_payment(user_id: int, amount: float):
    if amount > 999:
        raise ValueError(f"Amount {amount} exceeds limit")
    await asyncio.sleep(0.2)
    return f"paid:{user_id}:${amount}"

async def cleanup_old_jobs():
    print("    🧹 Cleaning up old jobs...")
    await asyncio.sleep(0.1)

FUNCTIONS = {
    "send_email":       send_email,
    "process_payment":  process_payment,
    "cleanup_old_jobs": cleanup_old_jobs,
}

# ── Run everything ───────────────────────────────────────────
async def main():
    pool = await get_pool(DATABASE_URL)
    await init_schema(pool)

    worker = PGWorker(pool, FUNCTIONS, concurrency=3, poll_interval=0.5)
    worker_task = asyncio.create_task(worker.run())

    # enqueue jobs
    id1 = await enqueue(pool, "send_email", kwargs={"to": "alice@ex.com", "subject": "Hi"})
    id2 = await enqueue(pool, "process_payment", kwargs={"user_id": 1, "amount": 50.0})
    id3 = await enqueue(pool, "process_payment", kwargs={"user_id": 2, "amount": 9999.0})  # will fail
    id4 = await enqueue(pool, "send_email", kwargs={"to": "bob@ex.com", "subject": "Later"}, delay_seconds=3)

    # wait for immediate jobs
    for jid in [id1, id2, id3]:
        result = await wait_for_result(pool, jid, timeout=15)
        print(f"  Result {jid[:8]}: {result['status']} → {result.get('result') or result.get('error')}")

    # let delayed job run
    await asyncio.sleep(5)

    # inspect DLQ
    dlq = await list_dlq(pool)
    print(f"\n  DLQ has {len(dlq)} job(s):")
    for j in dlq:
        print(f"    - {j['func_name']}[{j['job_id'][:8]}]: {j['error']}")

    worker.stop()
    await asyncio.sleep(0.5)
    await worker_task
    await close_pool()

asyncio.run(main())
```

---

## Useful Operational Queries

```sql
-- How many jobs per status?
SELECT status, COUNT(*) FROM jobs GROUP BY status;

-- Jobs stuck running (heartbeat older than 5 minutes)
SELECT job_id, func_name, worker_id, heartbeat_at
FROM jobs
WHERE status = 'running'
  AND heartbeat_at < NOW() - INTERVAL '5 minutes';

-- Rescue stuck jobs
UPDATE jobs
SET status = 'pending', worker_id = NULL, run_at = NOW()
WHERE status = 'running'
  AND heartbeat_at < NOW() - INTERVAL '5 minutes';

-- Throughput in the last hour
SELECT
    date_trunc('minute', finished_at) AS minute,
    COUNT(*) AS jobs_completed
FROM jobs
WHERE status = 'done'
  AND finished_at > NOW() - INTERVAL '1 hour'
GROUP BY 1
ORDER BY 1;

-- Average execution time per function
SELECT
    func_name,
    AVG(EXTRACT(EPOCH FROM (finished_at - started_at))) AS avg_seconds,
    MAX(EXTRACT(EPOCH FROM (finished_at - started_at))) AS max_seconds,
    COUNT(*) AS total
FROM jobs
WHERE status = 'done'
GROUP BY func_name;
```

---

## Project Layout

```
pgqueue/
├── __init__.py
├── schema.py          # CREATE TABLE statements
├── db.py              # connection pool + schema init
├── enqueue.py         # enqueue() — INSERT into jobs
├── dequeue.py         # dequeue() — SELECT FOR UPDATE SKIP LOCKED
├── worker.py          # PGWorker — polling loop, job execution
├── results.py         # mark_done, mark_failed, schedule_retry, move_to_dlq
├── dlq.py             # list_dlq, retry_dlq_job, retry_all_dlq
├── notify.py          # LISTEN/NOTIFY for instant job pickup
├── cron.py            # Recurring cron-style jobs
└── main.py            # Wiring it all together + example
```

---

## Comparison: All Three Queues

| Feature | asyncio.Queue | arq (Redis) | PostgreSQL Queue |
|---|---|---|---|
| Persistence | ❌ in-memory | ✅ Redis RDB/AOF | ✅ ACID |
| Multi-process | ❌ | ✅ | ✅ |
| SQL queries on jobs | ❌ | ❌ | ✅ |
| Extra infra needed | ❌ | Redis | ❌ (use existing PG) |
| Delayed jobs | manual | ✅ ZSET | ✅ run_at column |
| Throughput ceiling | very high | very high | ~1k jobs/sec |
| Setup complexity | none | low | medium |
| Best for | in-process work | microservices | monoliths + existing PG |

---

## What's Missing Before Production

| Feature | Status | How |
|---|---|---|
| Stuck job reaper | ❌ | Periodic query on heartbeat_at |
| Job cancellation | ❌ | UPDATE status='cancelled' + check in worker |
| Priorities per queue | ✅ | ORDER BY priority ASC in dequeue |
| Dashboard | ❌ | FastAPI endpoint + SQL queries above |
| Metrics | ❌ | Expose Prometheus counter from worker |
| Partitioning | ❌ | Partition jobs table by created_at for history |
| Multi-tenant queues | ✅ | queue column already supports it |
