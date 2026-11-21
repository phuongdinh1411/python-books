# 🔄 Python Queue Patterns — Guide

> Three production-grade queue implementations, from simplest to most powerful.
> Read this first to choose the right pattern for your problem.

---

## 🗺️ The Three Patterns

| File | Backend | Best for | Persistence | Distributed |
|------|---------|----------|-------------|-------------|
| [`01-asyncio-queue.md`](01-asyncio-queue.md) | In-memory | Single-process background tasks | ❌ Lost on crash | ❌ One process |
| [`02-arq-queue.md`](02-arq-queue.md) | Redis | Multi-process, high-throughput | ✅ AOF/RDB | ✅ Any machine |
| [`03-postgresql-queue.md`](03-postgresql-queue.md) | PostgreSQL | Audit trail, transactional, OLTP co-located | ✅ ACID | ✅ Any machine |

---

## 🎯 Decision Flowchart

```
Do you need jobs to survive a process restart?
│
├── NO  ──────────────────────────────────────────────────────────────────────
│         Use: asyncio.Queue (01-asyncio-queue.md)
│         When: FastAPI background processing, pipeline stages, in-process fans
│
└── YES ─────────────────────────────────────────────────────────────────────
          │
          Do you already have PostgreSQL and want SQL-queryable job history?
          │
          ├── YES ────────────────────────────────────────────────────────────
          │         Use: PostgreSQL Queue (03-postgresql-queue.md)
          │         When: Audit trails, low-latency delivery not needed,
          │               transactional enqueue ("enqueue only if DB row exists")
          │
          └── NO ─────────────────────────────────────────────────────────────
                    │
                    Do you need > 1,000 jobs/sec throughput?
                    │
                    ├── YES ─────────────────────────────────────────────────
                    │         Use: Redis Queue (02-arq-queue.md)
                    │         When: Email sending, image processing, webhooks,
                    │               high-volume event processing
                    │
                    └── NO ──────────────────────────────────────────────────
                              Either works — prefer Redis for simpler ops,
                              PostgreSQL to avoid adding a new service.
```

---

## 📊 Feature Comparison

| Feature | asyncio.Queue | Redis Queue | PostgreSQL Queue |
|---------|--------------|-------------|-----------------|
| **Setup complexity** | None | Redis instance | PostgreSQL (may already exist) |
| **Job durability** | ❌ | ✅ (AOF) | ✅ (ACID) |
| **Distributed workers** | ❌ | ✅ | ✅ |
| **Delayed jobs** | Custom | ✅ ZADD | ✅ `run_at` column |
| **Cron/recurring** | Custom | Custom | ✅ Advisory lock |
| **Priority queues** | ✅ PriorityQueue | Custom (sort set) | ✅ `ORDER BY priority` |
| **Job history/query** | In-memory dict | Redis HASH (TTL) | ✅ SQL forever |
| **Throughput** | 100k+/s | 50k+/s | 1k–5k/s |
| **Admin UI** | Health endpoint | RQ Dashboard / Flower | psql, Grafana, Metabase |
| **Transactional enqueue** | ❌ | ❌ | ✅ Same DB transaction |
| **Dead-letter queue** | In-memory deque | Redis LIST | PostgreSQL table |
| **Scheduled tasks (cron)** | ❌ | ❌ built-in | ✅ Advisory lock leader |
| **LISTEN/NOTIFY zero-latency** | N/A | N/A | ✅ |

---

## 🏗️ Architecture Patterns Covered

Each guide builds a full production system including:

### Common to all three:
- Job data model with status lifecycle (`pending → running → done/failed`)
- Worker pool with configurable concurrency
- Exponential backoff retry with full jitter (AWS-style)
- Dead-letter queue for permanently failed jobs
- Structured JSON logging
- Prometheus-compatible metrics
- Graceful shutdown with configurable drain timeout
- Full pytest test suite (unit + integration)
- Environment-variable driven configuration

### asyncio.Queue specific:
- Priority queue support (`asyncio.PriorityQueue`)
- In-memory result store
- HTTP health + metrics server (stdlib only, no extra deps)
- `contextvars` for per-job log tracing
- `asyncio.TaskGroup` worker pattern (Python 3.11+)

### Redis Queue specific:
- `BRPOP` blocking dequeue (zero CPU when idle)
- Delayed jobs via sorted set (`ZADD` with Unix timestamp score)
- Heartbeat + stuck-job reaper
- Atomic Lua dequeue script
- Result backend with configurable TTL
- FastAPI admin API (DLQ management, job inspection)
- msgpack serialization (3–5× smaller than JSON)
- Rate limiting per function (Redis INCR + EXPIRE)

### PostgreSQL Queue specific:
- `SELECT FOR UPDATE SKIP LOCKED` atomic dequeue
- Schema with partial indexes optimized for dequeue patterns
- LISTEN/NOTIFY for zero-latency job pickup (no polling needed)
- Cron scheduler with advisory lock leader election
- Full operational SQL runbook (inspect, retry, purge)
- Idempotent schema migrations
- `asyncpg` connection pool with health check
- Transactional enqueue (enqueue + DB write in same transaction)

---

## 🚀 Quick Start (All Three)

```bash
# asyncio.Queue (no dependencies)
python -m asyncio_queue.main

# Redis Queue
docker run -d -p 6379:6379 redis:7
pip install redis[asyncio] msgpack
python -m arq_queue.main

# PostgreSQL Queue
docker run -d -e POSTGRES_PASSWORD=secret -p 5432:5432 postgres:16
pip install asyncpg fastapi uvicorn
DATABASE_URL=postgresql://postgres:secret@localhost/queuedb \
    python -m pgqueue.main
```

---

## 📚 External Queue Libraries to Know

| Library | Backend | When to use |
|---------|---------|-------------|
| [**arq**](https://arq-docs.helpmanual.io/) | Redis | Drop-in production Redis queue; built by Pydantic author |
| [**celery**](https://docs.celeryq.dev/) | Redis/RabbitMQ | Battle-tested, large ecosystem, complex config |
| [**dramatiq**](https://dramatiq.io/) | Redis/RabbitMQ | Simpler than Celery, better defaults |
| [**rq**](https://python-rq.org/) | Redis | Simple Redis queue, great dashboard (RQ Dashboard) |
| [**SAQ**](https://github.com/tobymao/saq) | Redis | Async-native, similar to arq |
| [**procrastinate**](https://procrastinate.readthedocs.io/) | PostgreSQL | Production-grade PG queue library |
| [**apscheduler**](https://apscheduler.readthedocs.io/) | Various | Cron + interval scheduling |

> **Recommendation:** Use the custom implementations here to understand internals.
> In production: use `arq` for Redis, `procrastinate` for PostgreSQL.
> Roll your own only when you need maximum control.
