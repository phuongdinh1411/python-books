# Pillar 4 — Analytical & Columnar Stores

> **Duration:** 1 week | **Priority:** 🟡 Medium-High

---

## 🎯 Learning Objectives

- Understand WHY columnar storage is faster for analytics
- Use DuckDB for fast local analytics on Parquet / CSV / S3
- Understand the architecture of Snowflake, BigQuery, and Redshift
- Know when to use OLTP (PostgreSQL) vs OLAP (columnar) stores
- Design star and snowflake schemas for analytics workloads
- Use Apache Parquet as the universal analytics file format

---

## 📚 Resources

| Resource | Type | Priority |
|----------|------|----------|
| *Designing Data-Intensive Applications* — Kleppmann Ch 3 | 📖 Book | Must |
| [DuckDB Docs](https://duckdb.org/docs/) | 📄 Docs | Must |
| [The Parquet Format — blog.twitter.com](https://blog.twitter.com/engineering/en_us/a/2013/dremel-made-simple-with-parquet) | 📄 Article | Recommended |
| [Snowflake Architecture Docs](https://docs.snowflake.com/en/user-guide/intro-key-concepts) | 📄 Docs | Recommended |

---

## Section 1 — Row vs Columnar Storage

### Why Columnar Is Faster for Analytics

```
ROW STORAGE (PostgreSQL heap):
  Disk page contains full rows:
  [id=1, name="Alice", age=30, revenue=500.00]
  [id=2, name="Bob",   age=25, revenue=750.00]
  [id=3, name="Carol", age=35, revenue=300.00]

  Query: SELECT AVG(revenue) FROM customers;
  Problem: must READ every byte of every row just to access revenue!
           If row is 200 bytes and revenue is 8 bytes → 96% waste!

COLUMNAR STORAGE (Parquet, Redshift, Snowflake):
  Each column stored together:
  [name]:    [Alice, Bob, Carol]
  [age]:     [30, 25, 35]
  [revenue]: [500.00, 750.00, 300.00]  ← only this is read

  Query: SELECT AVG(revenue) FROM customers;
  - Reads ONLY the revenue column (column pruning)
  - Values are similar → compress very well (run-length encoding, dict encoding)
  - Can vectorize computation (SIMD)
```

### Compression Ratios

```
Columnar compression examples:
  status column: 'pending','completed','pending','pending','completed'
  → Dictionary encoding: {0:'pending', 1:'completed'}
  → Bit-packed: 0,1,0,0,1  (5 bits instead of 5×9 bytes = 45 bytes)
  → 90%+ compression!

  Timestamps in time-series:
  1704067200, 1704067201, 1704067202, 1704067203...
  → Delta encoding: 1704067200, +1, +1, +1...
  → Run-length: start=1704067200, delta=1, count=N
```

---

## Section 2 — DuckDB (The Local Analytical Engine)

DuckDB is an **in-process** analytical database — think SQLite but for analytics.
Runs queries directly on Parquet, CSV, JSON files. Zero infrastructure needed.

```bash
pip install duckdb
```

### Direct File Queries

```python
import duckdb

# Query CSV directly
result = duckdb.sql("""
    SELECT
        DATE_TRUNC('month', created_at) AS month,
        COUNT(*) AS orders,
        SUM(total) AS revenue
    FROM read_csv_auto('orders.csv')
    GROUP BY 1
    ORDER BY 1
""").df()

# Query Parquet files (single or glob)
duckdb.sql("""
    SELECT COUNT(*), AVG(total)
    FROM read_parquet('data/orders/*.parquet')
    WHERE status = 'completed'
""").show()

# Query remote S3 files
duckdb.sql("""
    INSTALL httpfs;
    LOAD httpfs;
    SELECT * FROM read_parquet('s3://my-bucket/data/orders.parquet')
    LIMIT 100
""")
```

### In-Memory and Persistent Mode

```python
import duckdb
import pandas as pd

# In-memory (default)
con = duckdb.connect()

# Persistent
con = duckdb.connect("analytics.duckdb")

# Register a Pandas DataFrame as a DuckDB table
df = pd.read_csv("large_file.csv")
con.register("orders_df", df)
result = con.execute("SELECT * FROM orders_df WHERE total > 100").df()

# Create persistent tables
con.execute("""
    CREATE TABLE IF NOT EXISTS orders AS
    SELECT * FROM read_parquet('s3://bucket/orders/*.parquet')
""")
```

### Advanced Analytics with DuckDB

```python
import duckdb

con = duckdb.connect()

# Window functions — same syntax as PostgreSQL
result = con.execute("""
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', created_at) AS month,
            SUM(total) AS revenue
        FROM read_parquet('orders.parquet')
        GROUP BY 1
    )
    SELECT
        month,
        revenue,
        SUM(revenue) OVER (ORDER BY month) AS running_total,
        revenue / LAG(revenue) OVER (ORDER BY month) - 1 AS mom_growth
    FROM monthly
    ORDER BY month
""").df()

# PIVOT (DuckDB 0.8+)
result = con.execute("""
    PIVOT orders
    ON status
    USING SUM(total)
    GROUP BY DATE_TRUNC('month', created_at)
""").df()
```

---

## Section 3 — Apache Parquet (The Universal Analytics Format)

Parquet is the standard file format for data lakes. Every data tool understands it.

### Writing and Reading Parquet with Python

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Write Parquet with optimal settings
df = pd.read_csv("orders.csv")

# Convert to PyArrow table with explicit schema
schema = pa.schema([
    ("id", pa.int64()),
    ("customer_id", pa.int32()),
    ("status", pa.dictionary(pa.int8(), pa.utf8())),  # dict encoding for low-cardinality
    ("total", pa.float64()),
    ("created_at", pa.timestamp("us", tz="UTC")),
])

table = pa.Table.from_pandas(df, schema=schema)

# Write with compression and row groups
pq.write_table(
    table,
    "orders.parquet",
    compression="snappy",          # snappy: fast, good compression (default)
    # compression="zstd",          # zstd: better compression, slightly slower
    row_group_size=100_000,        # rows per row group (affects read performance)
)

# Write partitioned dataset (best practice for large data)
pq.write_to_dataset(
    table,
    root_path="data/orders/",
    partition_cols=["status"],     # one folder per status value
    # Creates: data/orders/status=completed/part-0.parquet
    #          data/orders/status=pending/part-0.parquet
)

# Read
table = pq.read_table("orders.parquet")
df = table.to_pandas()

# Read only specific columns (column pruning)
df = pq.read_table("orders.parquet", columns=["id", "total", "created_at"]).to_pandas()

# Read with filter pushdown (skips row groups)
df = pq.read_table(
    "orders.parquet",
    filters=[("status", "=", "completed"), ("total", ">", 100.0)]
).to_pandas()

# Read partitioned dataset
dataset = pq.ParquetDataset(
    "data/orders/",
    filters=[("status", "=", "completed")]  # only reads matching partitions
)
df = dataset.read().to_pandas()
```

### Parquet Best Practices

```python
# 1. Choose good partition columns
# GOOD: low-ish cardinality (10s to 1000s of values), often filtered
pq.write_to_dataset(table, "data/", partition_cols=["year", "month", "status"])
# BAD: high cardinality (never partition by user_id or order_id!)

# 2. Row group size: balance between parallelism and filter pushdown
# Small row groups (10K) → better filter pushdown, more metadata overhead
# Large row groups (1M)  → fewer row group stats, but bigger reads
# Sweet spot: 100K–500K rows

# 3. Use Polars for faster Parquet processing
import polars as pl

df = pl.read_parquet(
    "data/orders/*.parquet",
    columns=["id", "total", "status"],   # column pruning
)
df.filter(pl.col("total") > 100).group_by("status").agg(pl.col("total").sum())
```

---

## Section 4 — Dimensional Modeling (Star Schema)

Analytics databases are designed with **star schemas**, not normalized schemas.

```
Normalized (OLTP):
  orders → order_items → products → categories
  Too many JOINs for analytics!

Star Schema (OLAP):
  Central FACT table surrounded by DIMENSION tables

                   ┌──────────────┐
                   │  dim_date    │
                   │  date_key PK │
                   └──────┬───────┘
                          │
  ┌──────────────┐    ┌───▼──────────────────┐    ┌──────────────┐
  │ dim_customer │    │   fact_orders         │    │ dim_product  │
  │ customer_key ├────┤ order_key      PK     ├────┤ product_key  │
  │ full_name    │    │ customer_key   FK      │    │ name         │
  │ country      │    │ product_key    FK      │    │ category     │
  │ segment      │    │ date_key       FK      │    │ brand        │
  └──────────────┘    │ quantity              │    └──────────────┘
                      │ unit_price            │
                      │ total_price           │
                      │ discount              │
                      └───────────────────────┘
```

```sql
-- Star schema SQL
-- Dimension tables: denormalized, descriptive
CREATE TABLE dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id  INTEGER,              -- source system key
    full_name    TEXT,
    email        TEXT,
    country      TEXT,
    city         TEXT,
    segment      TEXT,                 -- 'VIP', 'Regular', 'New'
    -- SCD Type 2 fields:
    valid_from   TIMESTAMPTZ,
    valid_to     TIMESTAMPTZ,
    is_current   BOOLEAN DEFAULT TRUE
);

-- Fact table: measurements, keys, no descriptions
CREATE TABLE fact_orders (
    order_key     SERIAL PRIMARY KEY,
    customer_key  INTEGER REFERENCES dim_customer(customer_key),
    product_key   INTEGER REFERENCES dim_product(product_key),
    date_key      INTEGER REFERENCES dim_date(date_key),
    quantity      INTEGER,
    unit_price    NUMERIC(10, 2),
    total_price   NUMERIC(10, 2),
    discount      NUMERIC(5, 2)
);

-- Analytics query on star schema: simple, fast
SELECT
    dc.country,
    dc.segment,
    dd.year,
    dd.month_name,
    SUM(fo.total_price)   AS revenue,
    COUNT(DISTINCT fo.order_key) AS orders,
    AVG(fo.total_price)   AS avg_order_value
FROM fact_orders fo
JOIN dim_customer dc ON fo.customer_key = dc.customer_key
JOIN dim_date     dd ON fo.date_key     = dd.date_key
JOIN dim_product  dp ON fo.product_key  = dp.product_key
WHERE dd.year = 2024
  AND dc.segment = 'VIP'
GROUP BY 1, 2, 3, 4
ORDER BY revenue DESC;
```

### Slowly Changing Dimensions (SCD)

```sql
-- SCD Type 2: keep history of changes
-- When a customer changes country, we keep the old record and add a new one

-- SCD2 upsert procedure
CREATE OR REPLACE PROCEDURE upsert_dim_customer(
    p_customer_id INTEGER,
    p_full_name TEXT,
    p_country TEXT,
    p_segment TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    existing_key INTEGER;
BEGIN
    -- Check if current record is different
    SELECT customer_key INTO existing_key
    FROM dim_customer
    WHERE customer_id = p_customer_id
      AND is_current = TRUE
      AND (full_name != p_full_name OR country != p_country OR segment != p_segment);

    IF FOUND THEN
        -- Expire old record
        UPDATE dim_customer
        SET valid_to = NOW(), is_current = FALSE
        WHERE customer_key = existing_key;

        -- Insert new record
        INSERT INTO dim_customer (customer_id, full_name, country, segment, valid_from, is_current)
        VALUES (p_customer_id, p_full_name, p_country, p_segment, NOW(), TRUE);
    ELSIF NOT FOUND THEN
        -- No current record exists — insert fresh
        INSERT INTO dim_customer (customer_id, full_name, country, segment, valid_from, is_current)
        VALUES (p_customer_id, p_full_name, p_country, p_segment, NOW(), TRUE)
        ON CONFLICT DO NOTHING;
    END IF;
END;
$$;
```

---

## Section 5 — Cloud Analytical Databases (Concepts)

### Snowflake

```
Architecture:
  Storage layer    → S3/Azure Blob/GCS — Parquet files (micro-partitions)
  Compute layer    → Virtual Warehouses (independent, auto-suspend)
  Services layer   → metadata, optimizer, auth

Key features:
  - Separation of storage and compute (scale independently)
  - Zero-copy cloning (clone 10TB DB instantly — just metadata!)
  - Time Travel (query historical data: SELECT * FROM t AT(offset => -3600))
  - Automatic clustering (micro-partition pruning)
  - Semi-structured data: VARIANT type (like JSONB)
```

```sql
-- Snowflake-specific SQL
-- Time travel
SELECT * FROM orders AT (OFFSET => -60*60);  -- 1 hour ago
SELECT * FROM orders BEFORE (STATEMENT => 'statement_id');

-- Zero-copy clone
CREATE TABLE orders_backup CLONE orders;

-- VARIANT (semi-structured)
SELECT
    raw_data:order_id::INTEGER AS order_id,
    raw_data:customer.email::VARCHAR AS email
FROM events_raw;

-- Stream (CDC — change data capture)
CREATE STREAM orders_stream ON TABLE orders;
SELECT * FROM orders_stream WHERE METADATA$ACTION = 'INSERT';
```

### BigQuery

```sql
-- BigQuery-specific features

-- Partitioned tables (auto-managed)
CREATE TABLE `project.dataset.orders`
PARTITION BY DATE(created_at)
CLUSTER BY customer_id, status
AS SELECT * FROM `project.staging.orders`;

-- Approximate aggregations (for huge tables)
SELECT APPROX_COUNT_DISTINCT(customer_id) FROM orders;  -- much faster than COUNT(DISTINCT)
SELECT APPROX_QUANTILES(total, 100) FROM orders;        -- percentiles

-- Array and struct (nested/repeated fields)
SELECT
    order_id,
    items,                             -- ARRAY<STRUCT<...>>
    items[OFFSET(0)].product_id AS first_product
FROM orders;

-- UNNEST arrays
SELECT o.order_id, item.product_id, item.quantity
FROM orders o, UNNEST(o.items) AS item;
```

---

## 🏋️ Exercises

### Exercise 1 — DuckDB Analytics
Download a public dataset (NYC Taxi data: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
in Parquet format. Use DuckDB to:
- Find the top 10 busiest pickup locations
- Calculate average fare by hour of day
- Compute month-over-month revenue growth

### Exercise 2 — Build a Star Schema
Take the e-commerce schema from Pillar 1 and transform it into a star schema:
- Create `dim_customer`, `dim_product`, `dim_date`, `fact_orders`
- Write an ETL query to populate fact_orders from the OLTP tables
- Write 3 analytics queries against the star schema

### Exercise 3 — Parquet Optimization
1. Write a 10M row DataFrame to Parquet with different settings (row_group_size, compression)
2. Measure read time for a filtered query with each setting
3. Demonstrate column pruning vs full scan performance difference

---

## ✅ Self-Check Questions

1. Why is columnar storage faster for `SELECT AVG(revenue) FROM orders`?
2. What is dictionary encoding in Parquet?
3. What is a row group and why does its size matter?
4. What is partition pruning?
5. What is the difference between a star schema and a snowflake schema?
6. What is a Slowly Changing Dimension (SCD) Type 2?
7. What is a fact table and what does it contain?
8. What makes DuckDB special compared to PostgreSQL?
9. What is Snowflake's Virtual Warehouse and why is it useful?
10. When would you choose columnar storage over row storage?

---

## 🔗 Key Links

- https://duckdb.org/docs/
- https://parquet.apache.org/documentation/latest/
- https://docs.snowflake.com/
- https://cloud.google.com/bigquery/docs
- https://www.kimballgroup.com/ (dimensional modeling bible)
