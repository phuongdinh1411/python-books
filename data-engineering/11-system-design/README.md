# Pillar 11 — System Design for Data Engineers

> **Duration:** 1 week | **Priority:** 🔴 Critical for Senior roles
> **WorldQuant angle:** Every senior JD says *"design distributed, scalable,
> fault-tolerant systems; event-driven architecture; ETL/ELT pipelines"*.
> This pillar turns everything in Pillars 1–10 into interview-ready narratives.

---

## 🎯 Learning Objectives

- Fluently walk through any data system design in 40 minutes
- Know the standard tradeoffs (batch vs stream, push vs pull, strong vs eventual)
- Apply the right patterns: idempotency, exactly-once, backpressure, fan-out, SCD
- Design with failure in mind: retries, dead-letters, circuit breakers, replay
- Draw and explain the Bronze/Silver/Gold + Lambda + Kappa architectures

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [*Designing Data-Intensive Applications*](https://dataintensive.net/) — Kleppmann | 📖 Book | Library/O'Reilly |
| [ByteByteGo — System Design Newsletter](https://bytebytego.com/) | 📄 Newsletter | Free tier |
| [Martin Kleppmann — Lecture Notes (YouTube)](https://www.youtube.com/playlist?list=PLeKd45zvjcDFUEv_ohr_HdUFe97RItdiB) | 🎥 Video | ✅ Free |
| [The Data Engineering Cookbook](https://github.com/andkret/Cookbook) | 📄 PDF | ✅ Free |
| Pillars 5–8 of this course | 📄 This repo | ✅ Free |

---

## Section 1 — Interview Framework (40-Minute Template)

Use this structure for every system design question. The interviewer is scoring
your *thinking process*, not just the final diagram.

```
 0–5 min   CLARIFY — scope, scale, constraints, non-goals
 5–15 min  HIGH-LEVEL DESIGN — components, data flow, APIs
15–30 min  DEEP DIVE — the hardest sub-problem (storage, queue, consistency)
30–35 min  FAILURE HANDLING — retries, DLQ, replay, monitoring
35–40 min  TRADEOFFS & ALTERNATIVES — what you chose and why you didn't pick X
```

### Clarifying Questions to Always Ask

```
Scale:
  - How many events/records per second at peak?
  - How much data per day? Per year?
  - How many concurrent readers/writers?

Consistency:
  - Is exactly-once required, or is at-least-once + deduplication acceptable?
  - What is the acceptable latency? (sub-second? minutes? hours?)
  - Is strong consistency needed, or eventual consistency OK?

Reliability:
  - What is the SLA? (99.9% = 8.7 hrs downtime/year, 99.99% = 52 min)
  - What happens if a component goes down — data loss acceptable?

Scope:
  - Is this greenfield or migrating an existing system?
  - Any existing infrastructure constraints (must use Kafka, must use AWS)?
  - Are there regulatory requirements (data residency, audit trails)?
```

---

## Section 2 — Design 1: Large-Scale ETL Pipeline

> **Most likely WorldQuant question.** JD verbatim: *"design, build, and operate
> large-scale data and ETL systems that power the firm's research and investment workflows"*

### Problem Statement
Design a system that ingests financial data from 10+ heterogeneous sources
(REST APIs, SFTP drops, database CDC, market data vendors), normalizes it,
validates quality, and makes it available for downstream research within 15 minutes
of source availability.

**Scale:** 500GB/day raw data, 50+ downstream consumers, 5-year history.

### Clarifications to surface
- Batch or streaming? → Both: vendors push daily files (batch) + real-time tick feeds (stream)
- Idempotency required? → Yes — re-running a pipeline day must produce same result
- Schema changes: → Sources change schema without notice — must handle gracefully
- SLA: → Raw data available in Bronze within 5 min; normalized Silver within 15 min

### High-Level Design

```
                    ┌─────────────────────────────────────────────────────┐
                    │              DATA SOURCES                           │
                    │  REST APIs  │  SFTP/S3  │  DB CDC  │  Market Feeds │
                    └──────┬──────┴─────┬─────┴────┬─────┴───────┬───────┘
                           │            │          │             │
                    ┌──────▼────────────▼──────────▼─────────────▼───────┐
                    │              INGESTION LAYER                        │
                    │   Airflow DAGs (batch)  │  Kafka (streaming CDC)    │
                    │   Source connectors     │  Debezium (DB changes)    │
                    └──────────────────────────────────┬──────────────────┘
                                                       │
                    ┌──────────────────────────────────▼──────────────────┐
                    │              BRONZE LAYER  (Raw)                    │
                    │   Delta Lake / S3 Parquet — append-only, never      │
                    │   modified. Exact copy of source. Infinite history. │
                    └──────────────────────────────────┬──────────────────┘
                                                       │  PySpark / dbt
                    ┌──────────────────────────────────▼──────────────────┐
                    │              SILVER LAYER  (Clean)                  │
                    │   Validated, typed, deduplicated, schema-enforced.  │
                    │   Delta Lake with MERGE (upsert). Point-in-time OK. │
                    └──────────────────────────────────┬──────────────────┘
                                                       │  dbt models
                    ┌──────────────────────────────────▼──────────────────┐
                    │              GOLD LAYER  (Serving)                  │
                    │   Star schema, pre-aggregated, business-ready.      │
                    │   PostgreSQL DW + Parquet for bulk reads.           │
                    └──────────────────────────────────┬──────────────────┘
                                                       │
                    ┌──────────────────────────────────▼──────────────────┐
                    │              SERVING LAYER                          │
                    │   REST API (FastAPI)  │  DuckDB ad-hoc  │  BI tools │
                    └─────────────────────────────────────────────────────┘
```

### Deep Dive: Idempotency

This is the #1 correctness concern in ETL. Re-running a pipeline twice must
produce **the same result** as running it once.

```python
# Pattern 1: Upsert (not append)
# Every load uses INSERT ... ON CONFLICT DO UPDATE instead of INSERT
# Same source record loaded twice → same DB row, no duplicate

# Pattern 2: Partition-replace
# Overwrite the full partition for a date instead of appending
spark.write.format("delta") \
    .mode("overwrite") \
    .option("replaceWhere", "date = '2024-01-15'") \
    .save("s3://lake/silver/prices/")
# Running this twice for the same date → same data, no duplicates

# Pattern 3: Watermark + dedup key
# Keep a "last_processed_at" watermark per source
# On each run: only fetch records updated after the watermark
# Dedup by (source_id, record_id) in target table

# Pattern 4: Content hash
# Hash the payload → use hash as the idempotency key
import hashlib
import json

def content_hash(record: dict) -> str:
    canonical = json.dumps(record, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
```

### Deep Dive: Schema Evolution

Sources change schema without notice. The pipeline must not break.

```python
# Bronze: accept any schema (schema-on-read)
# Store raw bytes / JSON — never enforce schema at write time
df = spark.read.option("inferSchema", "false").json("s3://raw/vendor_a/")

# Silver: enforce canonical schema, quarantine invalid rows
from pyspark.sql import functions as F

def enforce_and_quarantine(df, expected_schema):
    """Cast to expected types; rows that fail go to quarantine table."""
    valid = df.select([
        F.col(f.name).cast(f.dataType).alias(f.name)
        for f in expected_schema.fields
    ])
    nulls = valid.filter(
        F.col("id").isNull() | F.col("symbol").isNull()
    )
    good = valid.filter(
        F.col("id").isNotNull() & F.col("symbol").isNotNull()
    )
    if nulls.count() > 0:
        nulls.write.format("delta").mode("append").save("s3://quarantine/")
    return good

# Schema registry (Confluent): enforce at Kafka level
# Producers register schema; consumers get type-safe deserialization
# Schema compatibility modes: BACKWARD (new can read old), FORWARD (old can read new)
```

### Deep Dive: Backpressure

When downstream is slower than upstream, you must not lose data or crash.

```python
# Kafka: natural backpressure via consumer offset lag
# Consumer slows down → offset lag grows → producer is unaffected
# Monitor: kafka-consumer-groups --describe | watch the LAG column

# Spark Structured Streaming: maxOffsetsPerTrigger
spark.readStream.format("kafka") \
    .option("maxOffsetsPerTrigger", 100_000) \  # limit per micro-batch
    .load()
# If processing is slower than arrival: lag grows, triggering more batches

# Airflow DAG: pool + concurrency limits
# pools limit how many tasks run simultaneously
# If DB is slow → tasks queue in pool → DAG doesn't crash

# asyncio: bounded queue
queue = asyncio.Queue(maxsize=1000)
# Producer blocks when full (backpressure) instead of growing unbounded
```

### Key Tradeoffs to Discuss

| Decision | Option A | Option B | Choose When |
|----------|----------|----------|-------------|
| Batch vs stream | Airflow batch | Kafka streaming | Batch if latency > 5 min OK; stream otherwise |
| ETL vs ELT | Transform in pipeline code | Transform in warehouse (dbt) | ELT if DW is powerful + SQL teams own transforms |
| Row vs columnar store | PostgreSQL (OLTP) | Parquet/DuckDB (OLAP) | Row for writes + point lookups; columnar for analytics |
| Reprocess strategy | Recompute from Bronze | Store raw + transforms separately | Always store raw so you can reprocess with new logic |
| Schema enforcement | Bronze (strict) | Silver (strict) | Bronze: accept everything; enforce in Silver |

### Failure Modes to Address

```
Source goes down:
  → Airflow retries with exponential backoff
  → Alert on 3 consecutive failures
  → SLA miss notification to on-call

Bad data batch from source:
  → Failed rows → quarantine table (not lost)
  → Pipeline continues processing valid rows
  → Quarantine reviewed by data quality team

Pipeline job crashes mid-run:
  → Idempotent writes: re-run picks up where it left off
  → Bronze is append-only: partial run doesn't corrupt history
  → Silver uses MERGE: re-run updates to correct state

Schema change breaks Silver:
  → Bronze preserved raw → reprocess Silver with new schema
  → dbt tests catch regressions before Gold is affected
```

---

## Section 3 — Design 2: Real-Time Market Data Pipeline

### Problem Statement
Design a system that ingests tick-by-tick market data from 20 exchanges
(10M events/sec at peak), normalizes it, computes 1-min/5-min/1-hour OHLCV bars,
and makes it available to 50+ downstream research services with < 500ms latency.

**Scale:** 10M events/sec peak, 50 consumers, sub-second latency requirement.

### High-Level Design

```
20 Exchanges
    │ WebSocket / FIX / binary TCP
    ▼
┌─────────────────────────────────────────────────────────────┐
│  INGESTION TIER (stateless, scale-out)                      │
│  Exchange Adapters — normalize to canonical Tick schema     │
│  Protocol: FIX → Protobuf → Kafka                          │
└──────────────────────┬──────────────────────────────────────┘
                       │  Kafka (1 topic per exchange)
                       │  Partitioned by instrument_id
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PROCESSING TIER (Flink or Spark Structured Streaming)      │
│  Windowed aggregations: 1m / 5m / 1h OHLCV bars            │
│  Deduplication by (exchange, instrument, sequence_no)       │
│  Late data: 30-second watermark                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴────────────┐
           ▼                        ▼
┌──────────────────┐    ┌──────────────────────────────────┐
│  Time-Series DB  │    │  Kafka output topics             │
│  (InfluxDB /     │    │  bars.1m / bars.5m / bars.1h     │
│   TimescaleDB)   │    │  → downstream services subscribe │
└──────────────────┘    └──────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  SERVING TIER                    │
│  REST API: GET /bars/{sym}/{tf}  │
│  WebSocket push to research UIs  │
│  Redis cache (last 5 min bars)   │
└──────────────────────────────────┘
```

### Deep Dive: Exactly-Once vs At-Least-Once

```
At-least-once (simpler, cheaper):
  - Kafka producer retries on failure → may send duplicate ticks
  - Consumer processes and commits offset AFTER writing to DB
  - Idempotent consumer: deduplicate by (exchange, instrument, seq_no, timestamp)
  - Chosen for: most pipelines — duplicates are cheaper than complexity

Exactly-once (Kafka Transactions):
  - Kafka Transactions: atomic produce + offset commit
  - Producer: enable.idempotence=true + transactional.id
  - Consumer: isolation.level=read_committed
  - Cost: 10–20% throughput reduction
  - Chosen for: financial settlement, trade confirmations (never duplicate a trade)

For tick data: at-least-once + dedup is sufficient
  - A duplicate tick costs < 1μs to deduplicate
  - The complexity of Kafka Transactions at 10M/s is not worth it
```

### Deep Dive: Late Data Handling

Ticks arrive out of order due to network jitter and exchange delays.

```python
# Flink / Spark watermark: define how late data can be
stream.withWatermark("event_time", "30 seconds")  # accept up to 30s late
      .groupBy(
          F.window("event_time", "1 minute"),
          "instrument_id"
      ).agg(
          F.first("price").alias("open"),
          F.max("price").alias("high"),
          F.min("price").alias("low"),
          F.last("price").alias("close"),
          F.sum("volume").alias("volume"),
      )

# After watermark passes: window is finalized and emitted
# Late arrivals after watermark: dropped (or sent to late-data topic)

# Trade-off: larger watermark = more accurate bars but higher latency
# For 1-min bars: 30s watermark → results available 90s after window close
```

### Deep Dive: Fan-Out to 50 Consumers

```
Problem: 50 services all reading from the same Kafka topic is fine — that's what
consumer groups are for. Each group gets its own independent offset.

But: 50 services all querying the REST API for recent bars is not fine.

Solution: pub/sub at the serving layer

Option A — Kafka output topics (chosen):
  - Flink writes computed bars to: bars.1m, bars.5m, bars.1h
  - Each downstream service is its own consumer group
  - Backpressure handled naturally — slow consumers just lag

Option B — Redis Pub/Sub:
  - Push new bars to channel; subscribers receive in real time
  - No persistence — subscriber misses data if offline
  - Use for: dashboards and UIs, not for mission-critical consumers

Option C — WebSocket push:
  - API server pushes to connected research UIs
  - No polling overhead
  - Use for: interactive research tools

Design: combine all three
  Flink → Kafka output (durable, all services) ← primary
  API server → Redis Pub/Sub → WebSocket push  ← UI only
```

### Key Numbers to Know

```
Kafka throughput: ~100MB/s per broker, millions of msgs/sec
Kafka latency:    < 10ms end-to-end (producer → consumer)
Kafka retention:  default 7 days (configurable, up to petabytes)

TimescaleDB:      ~1M inserts/sec on commodity hardware (time-series optimized)
InfluxDB:         ~300K inserts/sec (purpose-built, compressed)
PostgreSQL:       ~50K inserts/sec with indexes (OLTP, not ideal for tick data)

Redis latency:    < 1ms for get/set
Flink throughput: 10M+ events/sec on a cluster
```

---

## Section 4 — Design 3: Distributed Job Scheduler (Like Airflow)

### Problem Statement
Design a workflow orchestration system where users define DAGs of dependent tasks,
schedule them (cron or event-triggered), and the system executes them reliably
across a fleet of workers with retries, alerting, and audit logs.

**Scale:** 10,000 DAG runs/day, 100,000 task executions/day, 500 workers.

### High-Level Design

```
┌───────────────────────────────────────────────────────────────┐
│  DAG AUTHORING                                                │
│  Python files in Git → CI validates → deployed to scheduler  │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│  SCHEDULER (single leader, elected via lock)                  │
│  - Parses DAG files every 30s                                 │
│  - Creates DAG Runs on cron schedule                          │
│  - Resolves task dependencies → enqueues READY tasks          │
│  - Updates task states: queued → running → success/failed     │
└───────────────────────────────┬───────────────────────────────┘
                                │  Task queue (Redis LIST or DB)
┌───────────────────────────────▼───────────────────────────────┐
│  WORKER FLEET  (N stateless workers, scale horizontally)      │
│  - Pull tasks from queue                                      │
│  - Execute task function (subprocess or thread)              │
│  - Report result back to scheduler (via DB or message)        │
│  - Heartbeat every 10s — reaper reclaims stuck tasks          │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│  METADATA DB  (PostgreSQL)                                    │
│  Tables: dag_runs, task_instances, dag_definitions            │
│  Source of truth for all state                                │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│  WEBSERVER  (read-only UI)                                    │
│  - Browse DAG runs, task logs, gantt charts                   │
│  - Trigger manual runs, clear failed tasks                    │
└───────────────────────────────────────────────────────────────┘
```

### Deep Dive: Exactly-Once Task Execution

The hardest problem: a worker crashes AFTER completing the task but BEFORE
reporting success. The scheduler retries the task → double execution.

```
Solutions by task type:

Idempotent tasks (safe to run twice):
  → No special handling needed
  → Example: "compute stats for 2024-01-15" — same result each time

Non-idempotent tasks (dangerous to run twice):
  → Idempotency key: before executing, write (dag_run_id, task_id) to a
    "completed_tasks" table atomically with the work
  → If record exists: skip execution, report success
  → Example: "send email notification" — check sent_emails table first

Outbox pattern (most reliable):
  → Worker writes task result + "mark_complete" message to DB in ONE transaction
  → Separate process reads outbox, marks task complete in scheduler DB
  → Even if worker crashes, outbox record is committed → retried safely
```

### Deep Dive: Dependency Resolution

```python
# DAG represented as adjacency list
dag = {
    "extract_orders":    [],
    "extract_customers": [],
    "join_orders":       ["extract_orders", "extract_customers"],
    "compute_metrics":   ["join_orders"],
    "send_report":       ["compute_metrics"],
}

# Topological sort → execution order
from collections import deque

def topological_sort(dag: dict[str, list[str]]) -> list[str]:
    in_degree = {node: 0 for node in dag}
    for node, deps in dag.items():
        for dep in deps:
            in_degree[node] += 1

    queue = deque(node for node, deg in in_degree.items() if deg == 0)
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        # Find tasks that depended on this node
        for candidate, deps in dag.items():
            if node in deps:
                in_degree[candidate] -= 1
                if in_degree[candidate] == 0:
                    queue.append(candidate)

    if len(result) != len(dag):
        raise ValueError("Cycle detected in DAG!")
    return result

# Scheduler loop:
# 1. topological_sort(dag) → ordered task list
# 2. For each task: check all deps have status=success
# 3. If yes: enqueue task (status=queued)
# 4. Worker picks up: status=running
# 5. On completion: status=success/failed
# 6. Scheduler wakes (via DB poll or LISTEN/NOTIFY): re-run step 2
```

### Deep Dive: Leader Election for Scheduler

Only ONE scheduler should run at a time (to avoid duplicate DAG runs).

```sql
-- PostgreSQL advisory lock for leader election
-- Scheduler tries to acquire lock every 10s
-- Only the lock holder runs the scheduling loop

SELECT pg_try_advisory_lock(123456789);  -- returns true if acquired

-- If true: I am the leader — run scheduling loop
-- If false: I am a standby — sleep and retry in 10s

-- Lock is automatically released if the process dies (session ends)
-- Standby notices within 10s and acquires leadership

-- Alternative: Zookeeper/etcd ephemeral node
-- Alternative: Redis SETNX with TTL + keepalive thread
```

---

## Section 5 — Design 4: Financial Data Warehouse

### Problem Statement
Design a data warehouse that stores 10 years of daily price/volume/fundamental data
for 50,000 instruments across 100 countries. It must support point-in-time correct
queries (critical for backtesting — no look-ahead bias) and serve 100 concurrent
research analysts.

**Scale:** 500GB structured data, 100 analysts, point-in-time correctness required.

### The Core Problem: Point-in-Time Correctness

```
Look-ahead bias = using data that wasn't available at time T when simulating time T
Example: Company reports earnings on 2024-02-15
         Analyst backtests strategy "as of 2024-01-01"
         If the warehouse returns Feb 15 earnings data for Jan 1 query → BIAS!

Solution: bi-temporal modeling — every row has TWO time dimensions:
  valid_time   = when the fact was true in the real world
  system_time  = when the fact was recorded in our system

Point-in-time query:
  "Give me all fundamentals as a researcher would have seen them on 2024-01-01"
  WHERE valid_time <= '2024-01-01'
    AND system_time <= '2024-01-01'  -- only data we had at that moment
  ORDER BY system_time DESC          -- latest revision known at that time
```

### Schema Design

```sql
-- Bi-temporal prices table
CREATE TABLE prices (
    id              BIGSERIAL PRIMARY KEY,
    instrument_id   INTEGER     NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    exchange        VARCHAR(10) NOT NULL,

    -- The fact
    open            NUMERIC(18,6),
    high            NUMERIC(18,6),
    low             NUMERIC(18,6),
    close           NUMERIC(18,6),
    volume          BIGINT,
    adj_close       NUMERIC(18,6),  -- corporate-action adjusted

    -- Bi-temporal columns
    valid_date      DATE        NOT NULL,  -- the trading day
    system_start    TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- when we learned this
    system_end      TIMESTAMPTZ NOT NULL DEFAULT 'infinity',  -- NULL if current

    -- Source tracking
    source          VARCHAR(50) NOT NULL,
    source_file     TEXT,
    etl_run_id      UUID
);

-- Current records only (99% of queries)
CREATE INDEX idx_prices_current ON prices (instrument_id, valid_date)
    WHERE system_end = 'infinity';

-- Point-in-time lookup
CREATE INDEX idx_prices_pit ON prices (instrument_id, valid_date, system_start);

-- Corporate action: a split happened — need to retroactively adjust prices
-- New rows: same valid_date, new system_start, old rows system_end = now
INSERT INTO prices (instrument_id, valid_date, close, adj_close, system_start)
VALUES (42, '2023-01-15', 150.00, 75.00, NOW());  -- 2:1 split adjustment

UPDATE prices SET system_end = NOW()
WHERE instrument_id = 42
  AND valid_date = '2023-01-15'
  AND system_end = 'infinity'
  AND system_start < NOW();
```

### Point-in-Time Query Pattern

```sql
-- "What prices would I have seen as of 2024-01-01?"
-- Correct for backtesting — no look-ahead bias

WITH pit_prices AS (
    SELECT
        instrument_id,
        valid_date,
        close,
        adj_close,
        ROW_NUMBER() OVER (
            PARTITION BY instrument_id, valid_date
            ORDER BY system_start DESC  -- most recent revision known at that time
        ) AS rn
    FROM prices
    WHERE valid_date <= '2024-01-01'          -- only valid before query date
      AND system_start <= '2024-01-01'         -- only data known at query date
)
SELECT instrument_id, valid_date, close, adj_close
FROM pit_prices
WHERE rn = 1  -- latest revision known at query time
ORDER BY instrument_id, valid_date;
```

### Partitioning Strategy

```sql
-- Partition by year for fast range scans
CREATE TABLE prices PARTITION BY RANGE (valid_date);

CREATE TABLE prices_2020 PARTITION OF prices
    FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
CREATE TABLE prices_2021 PARTITION OF prices
    FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
-- ...

-- Query for one year only reads that partition
EXPLAIN SELECT * FROM prices
WHERE valid_date BETWEEN '2024-01-01' AND '2024-12-31';
-- Partition Pruning: only scans prices_2024 → 10x faster than full table scan
```

---

## Section 6 — Design 5: Backtesting Engine

### Problem Statement
Design a system where researchers can submit a trading strategy (Python function +
parameters), run it against 10 years of historical data for 5,000 instruments,
and get results (Sharpe ratio, max drawdown, returns) within 5 minutes.

### High-Level Design

```
Researcher submits strategy:
    POST /backtest { "strategy_code": "...", "universe": "SP500",
                     "start": "2014-01-01", "end": "2024-01-01" }
                     ↓
         ┌───────────────────────────────┐
         │  API Server (FastAPI)         │
         │  Validate code (sandboxed)    │
         │  Enqueue backtest job         │
         │  Return job_id immediately    │
         └───────────────┬───────────────┘
                         │  Job queue (Redis / PostgreSQL)
                         ▼
         ┌───────────────────────────────────────────────────┐
         │  BACKTEST WORKER POOL                             │
         │  Dequeue job → fetch historical data              │
         │  Chunk by instrument (parallelism)                │
         │                                                   │
         │  For each instrument:                             │
         │    for date in date_range:                        │
         │      signal = strategy(historical_data_at(date))  │
         │      position = execute_signal(signal, prices)    │
         │      pnl.append(compute_pnl(position, next_price))│
         │                                                   │
         │  Aggregate → Sharpe, drawdown, returns            │
         └───────────────┬───────────────────────────────────┘
                         │
         ┌───────────────▼───────────────┐
         │  RESULTS STORE                │
         │  PostgreSQL: metadata, stats  │
         │  S3/Parquet: full time series │
         └───────────────────────────────┘

Researcher polls: GET /backtest/{job_id}/status
                  GET /backtest/{job_id}/results
```

### Deep Dive: Avoiding Look-Ahead Bias

```python
class BacktestEngine:
    def __init__(self, universe: list[str], start: str, end: str):
        self._prices = load_prices_pit(universe, start, end)  # point-in-time

    def run(self, strategy: Callable) -> BacktestResult:
        pnl = {}
        for date in self._trading_days:
            # CRITICAL: only pass data available at market close of `date`
            # historical_data_at() uses the bi-temporal query from Section 5
            snapshot = self._prices.as_of(date)   # ← no look-ahead!
            signals = strategy(snapshot)           # researcher's function
            # Execute next trading day's open (simulating overnight decision)
            next_open = self._prices.at(date + 1_trading_day)
            pnl[date] = compute_pnl(signals, next_open)
        return BacktestResult(pnl)
```

### Deep Dive: Parallelism Strategy

```python
# 5,000 instruments × 10 years × 252 trading days = 12.6M rows
# Single-threaded: ~30 minutes → too slow

# Strategy 1: Instrument-level parallelism
# Each worker handles a subset of instruments
# Results aggregated at the end

# With ProcessPoolExecutor:
from concurrent.futures import ProcessPoolExecutor
import numpy as np

def run_single_instrument(args):
    instrument_id, strategy_fn, prices_df = args
    return _run_backtest(instrument_id, strategy_fn, prices_df)

with ProcessPoolExecutor(max_workers=32) as pool:
    # Split 5,000 instruments across 32 processes
    futures = [
        pool.submit(run_single_instrument, (inst_id, strategy, data))
        for inst_id, data in price_data.items()
    ]
    results = [f.result() for f in futures]

# Strategy 2: Spark for massive parallelism
# Treat each (instrument, date) as a row
# Apply strategy as a Pandas UDF (vectorized)
from pyspark.sql.functions import pandas_udf

@pandas_udf("double")  # returns signal for each row
def compute_signal(prices: pd.Series) -> pd.Series:
    return strategy(prices)

spark_df.groupBy("instrument_id").apply(compute_signal)
```

---

## Section 7 — Key Patterns Reference Card

### The 6 Data Engineering Patterns Every Interviewer Expects

```
1. IDEMPOTENCY
   Problem: re-running a pipeline creates duplicates
   Solution: upsert (ON CONFLICT DO UPDATE) or partition-replace
   Test: run pipeline twice → row count is the same

2. EXACTLY-ONCE DELIVERY
   Problem: a message processed twice causes double-spend / duplicate records
   Solution: Kafka transactions OR at-least-once + idempotent consumer (dedup key)
   Rule: use exactly-once only where truly needed (high cost); dedup is usually fine

3. BACKPRESSURE
   Problem: fast producer overwhelms slow consumer → OOM or data loss
   Solution: bounded queue (Kafka partition, asyncio.Queue(maxsize=N))
   Kafka: consumer lag is the natural backpressure signal

4. POINT-IN-TIME CORRECTNESS
   Problem: backtesting uses future data → false signal
   Solution: bi-temporal table (valid_time + system_time)
   Query: WHERE system_start <= 'as_of_date'

5. SCHEMA EVOLUTION
   Problem: source changes schema → pipeline breaks
   Solution: Bronze accepts any schema (raw); Silver enforces + quarantines bad rows
   Tool: Delta Lake schema evolution (MERGE SCHEMA option)

6. FAULT ISOLATION
   Problem: one bad source/vendor takes down the whole pipeline
   Solution: pipeline per source, independent failure domains
   Airflow: separate DAGs per source; failure in one doesn't block others
```

### CAP Theorem Applied to Data Systems

```
Consistency + Availability — no Partition Tolerance:
  → Traditional RDBMS (PostgreSQL single-node)
  → Use when: ACID required, single-region, low volume

Consistency + Partition Tolerance — no Availability:
  → HBase, Zookeeper, etcd
  → Use when: distributed coordination, never return stale data

Availability + Partition Tolerance — no Consistency:
  → Cassandra, DynamoDB, Kafka (eventual consistency)
  → Use when: high write throughput, eventual consistency OK

For financial data:
  - Price ticks: AP (Availability + Partition) — stale tick is OK
  - Trade settlement: CP (Consistency + Partition) — never lose a trade
  - Research DW: CP with relaxed availability — accuracy over uptime
```

---

## 🏋️ Practice Problems

### Problem 1 — Design a Financial Data Ingestion System
*WorldQuant JD: "ingest data from multiple market data vendors, normalize it, store for research"*

You have 15 market data vendors, each with different formats (CSV, JSON, FIX protocol,
proprietary binary). Vendors push data at different times. Some are real-time (tick),
some are end-of-day batches. Design the ingestion and normalization system.

**Draw:** component diagram + data flow
**Discuss:** schema evolution, idempotency, failure isolation, monitoring

### Problem 2 — Design a Real-Time Signal Computation Pipeline
*WorldQuant JD: "event-driven architecture, streaming data"*

Researchers define alpha signals as Python functions of recent price/volume data.
The system must compute these signals in real time as new ticks arrive and
publish results to downstream position management systems.

**Draw:** component diagram
**Discuss:** exactly-once vs at-least-once, backpressure, fan-out

### Problem 3 — Scale Your ETL Pipeline 10x
*Classic follow-up question*

Your pipeline currently processes 50GB/day in 30 minutes.
The business just acquired a new data source: 500GB/day, same 30-minute SLA.
How do you scale it?

**Talk through:** partitioning strategy, horizontal vs vertical scaling,
Spark vs single-machine, storage tier optimization

---

## ✅ Self-Check Questions

1. What is the difference between ETL and ELT? When would you choose each?
2. What does idempotency mean for a data pipeline? How do you implement it?
3. What is backpressure? How does Kafka handle it naturally?
4. What is look-ahead bias and how does bi-temporal modeling prevent it?
5. What is the Bronze/Silver/Gold (Medallion) architecture?
6. How does `SELECT FOR UPDATE SKIP LOCKED` enable safe distributed dequeue?
7. What is the difference between at-least-once and exactly-once delivery?
8. What is partition pruning and what enables it in both Kafka and PostgreSQL?
9. How do you design a pipeline to handle schema changes from upstream sources?
10. A pipeline job fails halfway through a 10M-row load. How do you recover?
11. What is the CAP theorem? Where does Kafka sit?
12. How do you fan-out computed results to 50 downstream consumers efficiently?

---

## 🔗 Key Links

- https://dataintensive.net/ — DDIA (the bible)
- https://bytebytego.com/ — system design patterns
- https://kafka.apache.org/documentation/ — Kafka docs
- https://airflow.apache.org/docs/ — Airflow docs
- https://docs.delta.io/ — Delta Lake (ACID on data lakes)
- https://www.startdataengineering.com/ — practical data engineering patterns
