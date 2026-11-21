# Pillar 2 — PostgreSQL Deep Dive

> **Duration:** 2 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Understand PostgreSQL's storage model (heap, TOAST, MVCC)
- Master all index types and choose the right one for each query
- Use advanced PostgreSQL features: JSONB, arrays, full-text search, partitioning
- Configure connection pooling with PgBouncer
- Understand VACUUM, autovacuum, and table bloat
- Apply PostgreSQL-specific optimizations for production workloads

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [PostgreSQL Official Docs](https://www.postgresql.org/docs/current/) | 📄 Docs | ✅ Free — bookmark ch 11, 14, 25 |
| [use-the-index-luke.com](https://use-the-index-luke.com/) | 🌐 Site | ✅ Free — index internals in depth |
| [pgexercises.com](https://pgexercises.com/) | 🌐 Interactive | ✅ Free |
| [pganalyze blog](https://pganalyze.com/blog) | 📄 Blog | ✅ Free |
| [explain.depesz.com](https://explain.depesz.com/) | 🛠️ Tool | ✅ Free — visualise EXPLAIN output |
| [PostgreSQL Wiki — Performance Optimization](https://wiki.postgresql.org/wiki/Performance_Optimization) | 📄 Wiki | ✅ Free |

> 💡 **Optional paid books:** *SQL Performance Explained* (Winand), *High Performance PostgreSQL* (Smith)

---

## Section 1 — How PostgreSQL Stores Data

### MVCC (Multi-Version Concurrency Control)

PostgreSQL never modifies rows in place. Instead:
- **UPDATE** = insert new row version + mark old one as deleted
- **DELETE** = mark old row as deleted (not physically removed)
- **VACUUM** = reclaim space from dead tuples

```
Heap page (8 KB):
┌────────────────────────────────────┐
│ Page header                         │
├────────────────────────────────────┤
│ ItemId 1 → tuple (xmin=100, xmax=0)│  ← live row (inserted by txn 100)
│ ItemId 2 → tuple (xmin=98,xmax=100)│  ← dead row (deleted by txn 100)
│ ItemId 3 → tuple (xmin=102,xmax=0) │  ← live row
│ ...free space...                    │
└────────────────────────────────────┘

xmin = transaction that created this version
xmax = transaction that deleted/updated this version (0 = still live)
```

```sql
-- See dead tuples accumulating
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_pct,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Manual VACUUM
VACUUM orders;              -- reclaim dead tuples
VACUUM ANALYZE orders;      -- reclaim + update statistics
VACUUM FULL orders;         -- full rewrite (locks table! rarely needed)
```

### TOAST — Large Values

Columns larger than ~2KB are compressed and stored in a separate TOAST table.

```sql
-- Check which columns use TOAST
SELECT
    attname AS column,
    attstorage AS storage_strategy,
    -- 'p'=plain, 'e'=external(no compress), 'x'=extended, 'm'=main
    pg_size_pretty(avg_width) AS avg_size
FROM pg_stats
WHERE tablename = 'your_table';
```

---

## Section 2 — Index Types

### B-Tree (Default — 90% of use cases)

```sql
-- B-Tree is the default
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_created ON orders (created_at DESC);

-- Composite index — ORDER MATTERS
CREATE INDEX idx_orders_customer_status ON orders (customer_id, status);
-- ✅ Supports: WHERE customer_id = 1
-- ✅ Supports: WHERE customer_id = 1 AND status = 'completed'
-- ❌ Does NOT support: WHERE status = 'completed' (leading col missing)

-- Index on expression
CREATE INDEX idx_orders_month ON orders (DATE_TRUNC('month', created_at));
-- Now this uses the index:
SELECT * FROM orders WHERE DATE_TRUNC('month', created_at) = '2024-01-01';

-- Partial index — only indexes matching rows
CREATE INDEX idx_orders_pending ON orders (created_at)
WHERE status = 'pending';
-- Small, fast index for a common filter
```

### Hash Index

```sql
-- Only for equality (=), NOT range (<, >, BETWEEN)
-- Faster than B-tree for equality on large keys (UUIDs, emails)
CREATE INDEX idx_customers_email_hash ON customers USING HASH (email);

-- Good for:
SELECT * FROM customers WHERE email = 'alice@example.com';

-- NOT good for:
SELECT * FROM customers WHERE email LIKE 'alice%';  -- needs B-tree
```

### GIN (Generalized Inverted Index) — Arrays, JSONB, Full-Text

```sql
-- For JSONB
CREATE INDEX idx_products_attrs ON products USING GIN (attributes);  -- JSONB column

-- Now fast:
SELECT * FROM products WHERE attributes @> '{"color": "red"}';
SELECT * FROM products WHERE attributes ? 'size';   -- has key

-- For arrays
CREATE INDEX idx_tags_arr ON posts USING GIN (tags);  -- text[] column
SELECT * FROM posts WHERE tags @> ARRAY['python', 'sql'];

-- For full-text search
CREATE INDEX idx_products_fts ON products
USING GIN (to_tsvector('english', name || ' ' || COALESCE(description, '')));
```

### GiST — Geometric, Range, Fuzzy

```sql
-- Range types
CREATE TABLE reservations (
    id SERIAL PRIMARY KEY,
    room_id INTEGER,
    during TSTZRANGE
);
CREATE INDEX idx_reservations_range ON reservations USING GiST (during);

-- Find overlapping reservations
SELECT * FROM reservations
WHERE during && '[2024-06-01, 2024-06-07)'::tstzrange;

-- PostGIS (geometric queries)
CREATE INDEX idx_locations_geo ON locations USING GiST (coordinates);
```

### BRIN (Block Range Index) — Huge Sorted Tables

```sql
-- Very small index for time-series or naturally ordered data
-- Only works if physical storage order correlates with column values
CREATE INDEX idx_events_time_brin ON events USING BRIN (occurred_at);
-- Index is ~10,000x smaller than B-tree!
-- Works for: SELECT * FROM events WHERE occurred_at BETWEEN x AND y
-- (because events are appended in time order)
```

---

## Section 3 — EXPLAIN ANALYZE in Depth

```sql
-- Always use EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) for real plans
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.*, c.full_name
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.status = 'completed'
  AND o.created_at > NOW() - INTERVAL '30 days';
```

### Reading the Plan

```
Gather  (cost=1234.56..5678.90 rows=1000 width=128) (actual time=12.3..45.6 rows=982 loops=1)
  ->  Hash Join  (cost=... rows=...) (actual time=... rows=... loops=4)
        Hash Cond: (o.customer_id = c.id)
        Buffers: shared hit=1200 read=350   ← hit=cache, read=disk
        ->  Seq Scan on orders o (...)
              Filter: ((status = 'completed') AND (created_at > ...))
              Rows Removed by Filter: 50000  ← BAD — scanning too many rows
        ->  Hash  (cost=...)
              ->  Seq Scan on customers c (...)

cost=startup..total    — planner's estimate
actual time=first..total — actual ms
rows=N                 — actual rows returned
loops=N                — times this node executed
Buffers: hit=N read=N  — N hit from cache, N read from disk (slow!)
```

### Key Warnings to Spot

```sql
-- 1. Seq Scan on large table = missing index
Seq Scan on orders  (rows=5000000)   -- 5M rows! needs an index

-- 2. Rows estimate way off = stale statistics
Seq Scan on orders  (cost=... rows=10000) (actual ... rows=1500000)
-- Fix: ANALYZE orders;

-- 3. Nested Loop with many iterations = wrong join type
Nested Loop  (loops=50000)   -- 50k iterations = very slow for large tables

-- 4. Hash Batches > 1 = not enough work_mem
Hash  (Batches=4 Memory Usage=4096kB)   -- spilling to disk!
-- Fix: SET work_mem = '256MB'; for this session
```

---

## Section 4 — Advanced PostgreSQL Features

### JSONB — Document Storage in Postgres

```sql
-- JSONB stores binary JSON — faster queries, supports indexing
CREATE TABLE products (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255),
    attributes JSONB
);

INSERT INTO products (name, attributes) VALUES
    ('Laptop', '{"brand": "Apple", "ram": 16, "colors": ["silver", "gray"], "specs": {"cpu": "M3", "storage": 512}}'),
    ('Phone',  '{"brand": "Samsung", "ram": 8, "colors": ["black"], "specs": {"cpu": "Snapdragon"}}');

-- Access operators
SELECT
    attributes -> 'brand'            AS brand_json,     -- returns JSON: "Apple"
    attributes ->> 'brand'           AS brand_text,     -- returns text: Apple
    attributes -> 'specs' ->> 'cpu'  AS cpu,            -- nested: M3
    attributes -> 'colors' -> 0      AS first_color,    -- array index
    attributes #>> '{specs, cpu}'    AS cpu_path        -- path operator
FROM products;

-- Filter
SELECT * FROM products
WHERE attributes ->> 'brand' = 'Apple';

SELECT * FROM products
WHERE attributes @> '{"brand": "Apple"}';          -- contains

SELECT * FROM products
WHERE attributes ? 'discount';                      -- has key?

SELECT * FROM products
WHERE attributes -> 'ram' > '12'::jsonb;            -- numeric comparison

-- Modify JSONB
UPDATE products
SET attributes = attributes
    || '{"on_sale": true}'                            -- merge/add key
    - 'discontinued'                                  -- remove key
WHERE id = 1;

-- Expand JSONB to rows
SELECT
    id,
    jsonb_object_keys(attributes) AS key
FROM products;

SELECT
    id,
    key,
    value
FROM products,
LATERAL jsonb_each_text(attributes);
```

### Arrays

```sql
CREATE TABLE posts (
    id      SERIAL PRIMARY KEY,
    title   TEXT,
    tags    TEXT[],
    scores  INTEGER[]
);

INSERT INTO posts (title, tags) VALUES
    ('Python Guide', ARRAY['python', 'programming', 'tutorial']),
    ('SQL Tips',     '{"sql", "database", "postgresql"}');

-- Array operations
SELECT
    tags,
    tags[1]              AS first_tag,          -- 1-indexed!
    array_length(tags, 1) AS num_tags,
    'python' = ANY(tags) AS has_python,
    tags @> ARRAY['sql'] AS has_sql             -- contains
FROM posts;

-- Search in arrays
SELECT * FROM posts WHERE tags && ARRAY['python', 'sql'];  -- overlap
SELECT * FROM posts WHERE tags @> ARRAY['python', 'tutorial'];  -- contains all

-- Aggregate into arrays
SELECT
    category,
    ARRAY_AGG(name ORDER BY name) AS product_names,
    ARRAY_AGG(DISTINCT price)     AS distinct_prices
FROM products
GROUP BY category;

-- Unnest (expand array to rows)
SELECT id, UNNEST(tags) AS tag FROM posts;
```

### Full-Text Search

```sql
-- tsvector: preprocessed document (stemmed, stopwords removed)
-- tsquery: search query

-- Convert text to tsvector
SELECT to_tsvector('english', 'The quick brown fox jumps over the lazy dog');
-- 'brown':3 'dog':9 'fox':4 'jump':5 'lazi':8 'quick':2

-- Search
SELECT * FROM products
WHERE to_tsvector('english', name || ' ' || COALESCE(description, ''))
      @@ to_tsquery('english', 'laptop & apple');

-- Stored tsvector column (more efficient)
ALTER TABLE products ADD COLUMN search_vector TSVECTOR;

UPDATE products
SET search_vector = to_tsvector('english', name || ' ' || COALESCE(description, ''));

CREATE INDEX idx_products_fts ON products USING GIN (search_vector);

-- Auto-update trigger
CREATE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english',
        NEW.name || ' ' || COALESCE(NEW.description, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_products_search
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- Ranked search with highlighting
SELECT
    id,
    name,
    ts_rank(search_vector, query) AS rank,
    ts_headline('english', name || ' ' || description, query) AS snippet
FROM products,
     to_tsquery('english', 'laptop | macbook') AS query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 20;
```

### Table Partitioning

```sql
-- Range partitioning by date — perfect for time-series data
CREATE TABLE events (
    id          BIGSERIAL,
    user_id     INTEGER,
    event_type  VARCHAR(100),
    occurred_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (occurred_at);

-- Create partitions (each month is its own physical table)
CREATE TABLE events_2024_01 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE events_2024_02 PARTITION OF events
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Index each partition
CREATE INDEX ON events_2024_01 (occurred_at);
CREATE INDEX ON events_2024_02 (occurred_at);

-- Queries automatically use only relevant partitions (partition pruning)
EXPLAIN SELECT * FROM events
WHERE occurred_at BETWEEN '2024-01-15' AND '2024-01-20';
-- Only scans events_2024_01, not all partitions!

-- List partitioning (by discrete values)
CREATE TABLE orders_by_region (
    id     SERIAL,
    region VARCHAR(50) NOT NULL
) PARTITION BY LIST (region);

CREATE TABLE orders_us   PARTITION OF orders_by_region FOR VALUES IN ('US', 'CA');
CREATE TABLE orders_eu   PARTITION OF orders_by_region FOR VALUES IN ('UK', 'DE', 'FR');
CREATE TABLE orders_asia PARTITION OF orders_by_region FOR VALUES IN ('JP', 'SG', 'IN');

-- Hash partitioning (distribute load evenly)
CREATE TABLE users_partitioned (
    id SERIAL
) PARTITION BY HASH (id);

CREATE TABLE users_p0 PARTITION OF users_partitioned FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE users_p1 PARTITION OF users_partitioned FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE users_p2 PARTITION OF users_partitioned FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE users_p3 PARTITION OF users_partitioned FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

### CTEs with Mutations (`INSERT`, `UPDATE`, `DELETE`)

```sql
-- Writable CTEs — powerful for data transformations
WITH deleted_orders AS (
    DELETE FROM orders
    WHERE status = 'cancelled'
      AND created_at < NOW() - INTERVAL '1 year'
    RETURNING *   -- return deleted rows
)
INSERT INTO orders_archive
SELECT * FROM deleted_orders;


-- UPSERT (INSERT ... ON CONFLICT)
INSERT INTO products (id, name, price, stock)
VALUES (1, 'Laptop', 999.99, 100)
ON CONFLICT (id) DO UPDATE
    SET price = EXCLUDED.price,
        stock = EXCLUDED.stock,
        updated_at = NOW();

-- ON CONFLICT DO NOTHING
INSERT INTO customers (email, full_name)
VALUES ('alice@example.com', 'Alice')
ON CONFLICT (email) DO NOTHING;
```

---

## Section 5 — Performance Tuning Config

```sql
-- Key PostgreSQL settings (postgresql.conf)

-- Memory
shared_buffers = 4GB              -- 25% of RAM; main buffer cache
work_mem = 256MB                  -- per sort/hash operation (multiply by connections!)
maintenance_work_mem = 1GB        -- for VACUUM, CREATE INDEX
effective_cache_size = 12GB       -- hint to planner (75% of RAM)

-- Checkpointing
max_wal_size = 4GB
checkpoint_completion_target = 0.9

-- Connections
max_connections = 100             -- use PgBouncer instead of increasing this!

-- Statistics
default_statistics_target = 500  -- default 100; higher = better plans, slower ANALYZE
-- Or per column:
ALTER TABLE orders ALTER COLUMN customer_id SET STATISTICS 500;
```

### Connection Pooling with PgBouncer

```ini
# pgbouncer.ini
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
pool_mode = transaction    # best performance for web apps
max_client_conn = 1000     # app connects here
default_pool_size = 25     # actual PG connections
min_pool_size = 5

# In your app: connect to PgBouncer (port 6432), not Postgres directly
```

---

## Section 6 — MySQL Differences (For Cross-DB Work)

```sql
-- Key differences between PostgreSQL and MySQL:

-- 1. String comparison: MySQL case-insensitive by default, PG case-sensitive
-- MySQL: WHERE name = 'alice' matches 'Alice'
-- PG: WHERE name ILIKE 'alice'   (use ILIKE for case-insensitive)

-- 2. LIMIT/OFFSET syntax (same) but MySQL lacks many window functions pre-8.0

-- 3. Auto-increment: MySQL uses AUTO_INCREMENT, PG uses SERIAL or IDENTITY
-- MySQL: id INT AUTO_INCREMENT PRIMARY KEY
-- PG:    id SERIAL PRIMARY KEY  (or BIGINT GENERATED ALWAYS AS IDENTITY)

-- 4. JSON: MySQL has JSON type, PG has JSONB (much more powerful)

-- 5. UPSERT syntax:
-- MySQL: INSERT INTO ... ON DUPLICATE KEY UPDATE col = VALUES(col)
-- PG:    INSERT INTO ... ON CONFLICT (col) DO UPDATE SET col = EXCLUDED.col

-- 6. Transactions: MySQL (InnoDB) supports them; PG always MVCC

-- 7. EXPLAIN: MySQL uses EXPLAIN FORMAT=JSON; PG uses EXPLAIN (ANALYZE, BUFFERS)

-- 8. Schema: MySQL "schema" = "database"; PG has real schemas within a DB
```

---

## Section 7 — Monitoring Live Queries and Locks

### pg_stat_activity — See What's Running Right Now

```sql
-- Active queries right now
SELECT
    pid,
    usename,
    application_name,
    state,                    -- active, idle, idle in transaction
    wait_event_type,
    wait_event,
    ROUND(EXTRACT(EPOCH FROM (NOW() - query_start))::numeric, 1) AS runtime_sec,
    LEFT(query, 100) AS query_snippet
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY runtime_sec DESC NULLS LAST;

-- Kill a runaway query (use pid from above)
SELECT pg_cancel_backend(12345);    -- sends SIGINT (graceful)
SELECT pg_terminate_backend(12345); -- sends SIGTERM (hard kill)
```

### pg_locks — Detect Lock Contention

```sql
-- Find blocking locks
SELECT
    blocked.pid     AS blocked_pid,
    blocked.query   AS blocked_query,
    blocking.pid    AS blocking_pid,
    blocking.query  AS blocking_query,
    blocked_activity.wait_event_type,
    blocked_activity.wait_event
FROM pg_locks blocked
JOIN pg_stat_activity blocked_activity ON blocked.pid = blocked_activity.pid
JOIN pg_locks blocking
    ON blocking.granted = TRUE
   AND blocked.relation = blocking.relation
   AND blocked.pid != blocking.pid
JOIN pg_stat_activity blocking_activity ON blocking.pid = blocking_activity.pid
WHERE NOT blocked.granted;

-- Lock types to know:
-- AccessShareLock      -- SELECT
-- RowShareLock         -- SELECT FOR UPDATE
-- RowExclusiveLock     -- INSERT, UPDATE, DELETE
-- ShareUpdateExclusiveLock -- VACUUM, ANALYZE, CREATE INDEX CONCURRENTLY
-- AccessExclusiveLock  -- DROP TABLE, ALTER TABLE, LOCK TABLE (blocks everything!)
```

### auto_explain — Log Slow Query Plans Automatically

```sql
-- Add to postgresql.conf (or SET for one session):
-- shared_preload_libraries = 'auto_explain'

-- Session-level (test without restart):
LOAD 'auto_explain';
SET auto_explain.log_min_duration = '500ms';  -- log plans for queries > 500ms
SET auto_explain.log_analyze = ON;
SET auto_explain.log_buffers = ON;
SET auto_explain.log_nested_statements = ON;

-- Now any slow query will log its full EXPLAIN ANALYZE to PostgreSQL log
-- grep 'Query Text' /var/log/postgresql/postgresql.log
```

---

## Section 8 — Replication Concepts (Read for Interviews)

```
Streaming Replication (Physical):
  Primary → WAL stream → Standby (bit-for-bit copy)
  Use case: HA failover, read replicas
  Lag check: SELECT * FROM pg_stat_replication;

Logical Replication:
  Primary → logical decoding → Subscriber
  Use case: selective table replication, zero-downtime migrations, CDC (Debezium)
  Lag check: SELECT * FROM pg_replication_slots;
```

```sql
-- Check replication lag on primary
SELECT
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    ROUND(EXTRACT(EPOCH FROM write_lag)::numeric, 3) AS write_lag_sec,
    ROUND(EXTRACT(EPOCH FROM replay_lag)::numeric, 3) AS replay_lag_sec
FROM pg_stat_replication;

-- Check replication slots (logical)
SELECT slot_name, plugin, active, restart_lsn,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag_size
FROM pg_replication_slots;
-- WARNING: unused slots block WAL cleanup -> disk can fill up!
-- Drop stale slots: SELECT pg_drop_replication_slot('slot_name');
```

---

## 🏋️ Exercises

### Exercise 1 — Index Design
Given a table with 10M rows, write queries and design the optimal indexes for:
- `WHERE status = 'active' AND created_at > NOW() - INTERVAL '7 days'`
- `WHERE email = 'user@example.com'`
- `WHERE full_text_search @@ to_tsquery('english', 'python & tutorial')`

### Exercise 2 — JSONB Analytics
Create a `user_profiles` table with a JSONB `preferences` column.
Write queries to: find users with a specific preference, update nested values,
and aggregate preference data.

### Exercise 3 — Partition by Month
Partition the `events` table by month. Load 2 years of test data.
Verify with `EXPLAIN ANALYZE` that queries use partition pruning.

### Exercise 4 — VACUUM Analysis
Create a table, perform many updates, observe dead tuple bloat,
run VACUUM, and verify cleanup in `pg_stat_user_tables`.

---

## ✅ Self-Check Questions

1. What is MVCC and what problem does it solve?
2. What is a dead tuple and how is it reclaimed?
3. When should you use GIN vs B-tree indexes?
4. What is a partial index and when would you use one?
5. What does `EXPLAIN (ANALYZE, BUFFERS)` tell you that `EXPLAIN` alone doesn't?
6. What is partition pruning and what enables it?
7. What is TOAST and when does PostgreSQL use it?
8. What does `pg_stat_user_tables` track?
9. What is the difference between `->>` and `->` in JSONB queries?
10. Why use PgBouncer instead of increasing `max_connections`?

---

## 🔗 Key Links

- https://www.postgresql.org/docs/current/indexes.html
- https://www.postgresql.org/docs/current/ddl-partitioning.html
- https://www.postgresql.org/docs/current/datatype-json.html
- https://explain.depesz.com/   ← paste EXPLAIN output for visualization
- https://pganalyze.com/blog
---

## Section 7 — Monitoring Live Queries and Locks

### pg_stat_activity — See What's Running Right Now

```sql
-- Active queries right now
SELECT
    pid,
    usename,
    application_name,
    state,                    -- active, idle, idle in transaction
    wait_event_type,
    wait_event,
    ROUND(EXTRACT(EPOCH FROM (NOW() - query_start))::numeric, 1) AS runtime_sec,
    LEFT(query, 100) AS query_snippet
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY runtime_sec DESC NULLS LAST;

-- Kill a runaway query (use pid from above)
SELECT pg_cancel_backend(12345);    -- sends SIGINT (graceful)
SELECT pg_terminate_backend(12345); -- sends SIGTERM (hard kill)
```

### pg_locks — Detect Lock Contention

```sql
-- Find blocking locks
SELECT
    blocked.pid     AS blocked_pid,
    blocked.query   AS blocked_query,
    blocking.pid    AS blocking_pid,
    blocking.query  AS blocking_query,
    blocked_activity.wait_event_type,
    blocked_activity.wait_event
FROM pg_locks blocked
JOIN pg_stat_activity blocked_activity ON blocked.pid = blocked_activity.pid
JOIN pg_locks blocking
    ON blocking.granted = TRUE
   AND blocked.relation = blocking.relation
   AND blocked.pid != blocking.pid
JOIN pg_stat_activity blocking_activity ON blocking.pid = blocking_activity.pid
WHERE NOT blocked.granted;

-- Lock types to know:
-- AccessShareLock      -- SELECT
-- RowShareLock         -- SELECT FOR UPDATE
-- RowExclusiveLock     -- INSERT, UPDATE, DELETE
-- ShareUpdateExclusiveLock -- VACUUM, ANALYZE, CREATE INDEX CONCURRENTLY
-- AccessExclusiveLock  -- DROP TABLE, ALTER TABLE, LOCK TABLE (blocks everything!)
```

### auto_explain — Log Slow Query Plans Automatically

```sql
-- Add to postgresql.conf (or SET for one session):
-- shared_preload_libraries = 'auto_explain'

-- Session-level (test without restart):
LOAD 'auto_explain';
SET auto_explain.log_min_duration = '500ms';  -- log plans for queries > 500ms
SET auto_explain.log_analyze = ON;
SET auto_explain.log_buffers = ON;
SET auto_explain.log_nested_statements = ON;

-- Now any slow query will log its full EXPLAIN ANALYZE to PostgreSQL log
-- grep 'Query Text' /var/log/postgresql/postgresql.log
```

---

## Section 8 — Replication Concepts (Read for Interviews)

```
Streaming Replication (Physical):
  Primary → WAL stream → Standby (bit-for-bit copy)
  Use case: HA failover, read replicas
  Lag check: SELECT * FROM pg_stat_replication;

Logical Replication:
  Primary → logical decoding → Subscriber
  Use case: selective table replication, zero-downtime migrations, CDC (Debezium)
  Lag check: SELECT * FROM pg_replication_slots;
```

```sql
-- Check replication lag on primary
SELECT
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    ROUND(EXTRACT(EPOCH FROM write_lag)::numeric, 3) AS write_lag_sec,
    ROUND(EXTRACT(EPOCH FROM replay_lag)::numeric, 3) AS replay_lag_sec
FROM pg_stat_replication;

-- Check replication slots (logical)
SELECT slot_name, plugin, active, restart_lsn,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag_size
FROM pg_replication_slots;
-- WARNING: unused slots block WAL cleanup -> disk can fill up!
-- Drop stale slots: SELECT pg_drop_replication_slot('slot_name');
```

