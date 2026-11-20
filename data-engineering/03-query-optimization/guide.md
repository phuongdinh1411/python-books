# Pillar 3 — Query Optimization

> **Duration:** 1 week | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Read and interpret any `EXPLAIN ANALYZE` plan
- Choose the right index type and column order
- Identify and fix slow query patterns (N+1, missing indexes, bad statistics)
- Use `pg_stat_statements` to find the top slowest queries in production
- Write optimizer-friendly SQL

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [use-the-index-luke.com](https://use-the-index-luke.com/) | 🌐 Site | ✅ Free — full content of *SQL Performance Explained* |
| [explain.depesz.com](https://explain.depesz.com/) | 🛠️ Tool | ✅ Free |
| [PostgreSQL: Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) | 📄 Docs | ✅ Free |
| [pganalyze Index Advisor](https://pganalyze.com/index-advisor) | 🛠️ Tool | ✅ Free (account required) |
| [pganalyze blog](https://pganalyze.com/blog) | 📄 Blog | ✅ Free |

> 💡 **Optional paid book:** *SQL Performance Explained* — Markus Winand (all content free at use-the-index-luke.com)

---

## Section 1 — The Optimization Workflow

```
1. FIND    → pg_stat_statements: which queries are slow?
2. EXPLAIN → understand the current plan
3. IDENTIFY → bottleneck: Seq Scan? Bad estimate? Sort? Join type?
4. FIX    → add index / rewrite query / update stats / tune config
5. VERIFY → re-run EXPLAIN, compare wall time
```

### Find Slow Queries with `pg_stat_statements`

```sql
-- Enable the extension (once)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 20 slowest queries by total time
SELECT
    query,
    calls,
    ROUND(total_exec_time::numeric, 2)        AS total_ms,
    ROUND((total_exec_time / calls)::numeric, 2) AS avg_ms,
    ROUND(stddev_exec_time::numeric, 2)       AS stddev_ms,
    rows,
    ROUND(rows::numeric / calls, 2)           AS avg_rows,
    shared_blks_hit + shared_blks_read        AS total_blocks,
    ROUND(shared_blks_hit::numeric /
          NULLIF(shared_blks_hit + shared_blks_read, 0) * 100, 2) AS cache_hit_pct
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Reset stats
SELECT pg_stat_statements_reset();
```

---

## Section 2 — Index Internals: B-Tree

Understanding HOW indexes work helps you design them correctly.

```
B-Tree index on orders(customer_id):

                    [500]
                  /       \
           [200, 350]     [650, 800]
           /    |   \     /    |    \
    [1..199] [200..349] [350..499] [500..649] ...

- Each node = one disk page (8KB)
- Leaf nodes: sorted values + pointer to heap row (ctid)
- Lookup: O(log n) — traverse from root to leaf
- Range scan: reach leaf, then follow linked list
```

### The Three-Star Scoring System for Indexes

```
★ One star   = narrows search space (WHERE clause matches index prefix)
★ Two stars  = rows already sorted (eliminates ORDER BY sort)
★★★ Three stars = index covers all needed columns (index-only scan)
```

```sql
-- Query:
SELECT customer_id, status, total
FROM orders
WHERE customer_id = 100
  AND status = 'completed'
ORDER BY created_at DESC;

-- ★ Index: (customer_id)             -- narrows by customer_id only
-- ★★ Index: (customer_id, created_at DESC)  -- sorted too
-- ★★★ Index: (customer_id, status, created_at DESC) INCLUDE (total)
--            -- covers everything, no heap access!

-- INCLUDE: add non-filter columns to avoid heap lookup
CREATE INDEX idx_orders_cover ON orders
    (customer_id, status, created_at DESC)
    INCLUDE (total);

EXPLAIN (ANALYZE, BUFFERS)
SELECT customer_id, status, total
FROM orders
WHERE customer_id = 100 AND status = 'completed'
ORDER BY created_at DESC;
-- Plan shows: "Index Only Scan" = fastest possible!
```

---

## Section 3 — Fixing Common Slow Query Patterns

### Pattern 1: Function on Indexed Column (Index Not Used!)

```sql
-- BAD: wrapping indexed column in a function defeats the index
SELECT * FROM orders WHERE DATE(created_at) = '2024-01-15';
-- Plan: Seq Scan (can't use index on created_at because DATE() wraps it)

-- GOOD: range on the original column
SELECT * FROM orders
WHERE created_at >= '2024-01-15' AND created_at < '2024-01-16';

-- OR: functional index
CREATE INDEX idx_orders_date ON orders (DATE(created_at));
SELECT * FROM orders WHERE DATE(created_at) = '2024-01-15';
-- Now uses the index!

-- Same trap with LOWER():
SELECT * FROM customers WHERE LOWER(email) = 'alice@example.com';  -- BAD
CREATE INDEX idx_customers_email_lower ON customers (LOWER(email)); -- functional index fix
```

### Pattern 2: Implicit Type Cast

```sql
-- BAD: int column vs string literal causes implicit cast
CREATE TABLE orders (id BIGINT, customer_id INTEGER, ...);
SELECT * FROM orders WHERE customer_id = '100';  -- string cast defeats index

-- GOOD: match types exactly
SELECT * FROM orders WHERE customer_id = 100;  -- integer literal

-- ALWAYS check column type with:
\d orders   -- psql
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'orders';
```

### Pattern 3: OR Conditions (May Not Use Index)

```sql
-- BAD: OR on different columns often causes Seq Scan
SELECT * FROM customers WHERE email = 'a@b.com' OR phone = '555-1234';

-- GOOD: UNION ALL (uses index on each)
SELECT * FROM customers WHERE email = 'a@b.com'
UNION ALL
SELECT * FROM customers WHERE phone = '555-1234'
  AND email != 'a@b.com';  -- avoid duplicates
```

### Pattern 4: Leading Wildcard

```sql
-- BAD: leading % makes index unusable
SELECT * FROM products WHERE name LIKE '%phone%';  -- Seq Scan

-- GOOD options:
-- 1. Full-text search (best for natural language)
SELECT * FROM products
WHERE to_tsvector('english', name) @@ plainto_tsquery('phone');

-- 2. pg_trgm for substring matching
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_products_name_trgm ON products USING GIN (name gin_trgm_ops);
SELECT * FROM products WHERE name LIKE '%phone%';  -- now uses index!
SELECT * FROM products WHERE name ILIKE '%PHONE%'; -- also indexed
```

### Pattern 5: SELECT * When Columns Are Large

```sql
-- BAD: SELECT * when you only need 2 columns forces heap fetch
SELECT * FROM products WHERE category = 'Electronics';

-- GOOD: only select needed columns (enables index-only scan)
SELECT id, name, price FROM products WHERE category = 'Electronics';

-- BETTER: covering index with INCLUDE
CREATE INDEX idx_products_category_cover ON products (category)
    INCLUDE (id, name, price);
-- Query now uses Index Only Scan — never touches heap!
```

### Pattern 6: N+1 in SQL (ORM-generated)

```sql
-- BAD: application runs 1 + N queries
-- SELECT * FROM customers LIMIT 100
-- Then for each customer: SELECT * FROM orders WHERE customer_id = ?

-- GOOD: single JOIN
SELECT
    c.id, c.full_name, c.email,
    COUNT(o.id) AS order_count,
    SUM(o.total) AS lifetime_value
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.full_name, c.email;
```

---

## Section 4 — Join Strategies

PostgreSQL chooses between three join algorithms:

```
Nested Loop   — good for small tables or small result sets
              — O(n*m) in worst case
              — uses index on inner table

Hash Join     — good for large unsorted tables
              — builds hash table on smaller side
              — only for equality joins

Merge Join    — good for pre-sorted data
              — requires both sides sorted on join key
              — O(n+m)
```

```sql
-- Force a join type to test alternatives
SET enable_nestloop = OFF;   -- disable nested loop
SET enable_hashjoin = OFF;   -- disable hash join
SET enable_mergejoin = OFF;  -- disable merge join

EXPLAIN SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id;

-- Reset
RESET enable_nestloop;
```

---

## Section 5 — Statistics and the Planner

The planner uses statistics from `pg_statistic` to estimate row counts.
Wrong estimates → wrong plans.

```sql
-- View column statistics
SELECT
    attname AS column,
    n_distinct,       -- estimate of distinct values (-1 = all unique, e.g. PK)
    correlation,      -- 1.0 = perfectly ordered, 0 = random, -1 = reverse ordered
    most_common_vals,
    most_common_freqs,
    histogram_bounds
FROM pg_stats
WHERE tablename = 'orders' AND attname = 'status';

-- Increase statistics target for a heavily-filtered column
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 500;
ANALYZE orders;

-- Check estimate accuracy
EXPLAIN (ANALYZE, FORMAT JSON)
SELECT * FROM orders WHERE status = 'pending' AND customer_id = 100;
-- Compare "Plan Rows" vs "Actual Rows"
-- If off by >10x: consider increasing statistics target
```

### Extended Statistics (Multi-Column Correlations)

```sql
-- If two columns are correlated (e.g. city & country), tell the planner
CREATE STATISTICS orders_customer_status ON customer_id, status FROM orders;
ANALYZE orders;
-- Now multi-column estimates are more accurate
```

---

## Section 6 — `pg_stat_statements` in Production

```sql
-- Set up monitoring dashboard for top queries

-- Queries consuming most I/O (disk reads)
SELECT
    LEFT(query, 80) AS query_snippet,
    calls,
    ROUND(total_exec_time::numeric / calls, 2) AS avg_ms,
    shared_blks_read AS disk_reads,
    shared_blks_hit  AS cache_hits,
    ROUND(shared_blks_hit::numeric /
          NULLIF(shared_blks_hit + shared_blks_read, 0) * 100, 2) AS hit_pct
FROM pg_stat_statements
WHERE shared_blks_read > 1000
ORDER BY shared_blks_read DESC
LIMIT 20;

-- Queries with high variability (spikes)
SELECT
    LEFT(query, 80) AS query_snippet,
    calls,
    ROUND(mean_exec_time::numeric, 2) AS mean_ms,
    ROUND(stddev_exec_time::numeric, 2) AS stddev_ms,
    ROUND(max_exec_time::numeric, 2) AS max_ms
FROM pg_stat_statements
ORDER BY stddev_exec_time DESC
LIMIT 20;
```

---

## Section 7 — VACUUM Strategy

```sql
-- Check tables that need vacuuming
SELECT
    schemaname || '.' || relname AS table_name,
    n_dead_tup,
    n_live_tup,
    ROUND(100 * n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
    last_autovacuum,
    autovacuum_count
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;

-- Tune autovacuum aggressively for high-write tables
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor = 0.01,  -- trigger at 1% dead (default: 20%)
    autovacuum_analyze_scale_factor = 0.005 -- analyze at 0.5% change
);
```

---

## 🏋️ Exercises

### Exercise 1 — Query Diagnosis
Run `pg_stat_statements` on a loaded database. Find the top 5 slowest queries.
For each: run `EXPLAIN (ANALYZE, BUFFERS)`, identify the bottleneck, and fix it.

### Exercise 2 — Index Challenge
Given a table of 5M events:
```sql
SELECT user_id, COUNT(*), MAX(occurred_at)
FROM events
WHERE event_type = 'purchase'
  AND occurred_at BETWEEN '2024-01-01' AND '2024-03-31'
GROUP BY user_id
ORDER BY COUNT(*) DESC
LIMIT 100;
```
Design the optimal index. Measure before/after with EXPLAIN ANALYZE.

### Exercise 3 — Rewrite for the Planner
Rewrite these queries to be optimizer-friendly:
1. `WHERE DATE(created_at) = CURRENT_DATE`
2. `WHERE LOWER(email) = $1`
3. `WHERE name LIKE '%search_term%'`
4. `WHERE status = 'active' OR status = 'trial'`

---

## ✅ Self-Check Questions

1. What does `Seq Scan` in an EXPLAIN plan mean?
2. What is an Index Only Scan and when does it happen?
3. What is the difference between Hash Join, Merge Join, and Nested Loop?
4. Why can wrapping a column in a function defeat an index?
5. What does `pg_stat_statements` measure?
6. What is the Three-Star system for index design?
7. What is the INCLUDE clause on an index?
8. How do you find queries with stale statistics?
9. What is `pg_trgm` used for?
10. Why should you increase `statistics_target` on some columns?

---

## 🔗 Key Links

- https://use-the-index-luke.com/
- https://explain.depesz.com/
- https://www.postgresql.org/docs/current/using-explain.html
- https://www.postgresql.org/docs/current/pgstatstatements.html
