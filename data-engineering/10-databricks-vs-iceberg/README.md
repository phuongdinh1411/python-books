# Databricks (Delta Lake) vs Apache Iceberg
## Comprehensive Comparison Guide

> **What this guide covers:**
> This compares two things at two levels:
> 1. **Table formats:** Delta Lake (Databricks' open format) vs Apache Iceberg (Netflix/Apple origin)
> 2. **Platforms/Ecosystems:** Databricks (commercial platform) vs the open Iceberg ecosystem (Spark, Flink, Trino, Snowflake, etc.)
>
> Understanding both levels is critical — you can use **Iceberg on Databricks**, and **Delta Lake outside of Databricks**.

---

## 📚 Free Resources

| Resource | Type | Link |
|----------|------|------|
| Delta Lake Official Docs | 📄 Docs | https://docs.delta.io/ |
| Apache Iceberg Official Docs | 📄 Docs | https://iceberg.apache.org/docs/latest/ |
| Databricks Documentation | 📄 Docs | https://docs.databricks.com/ |
| Iceberg vs Delta Lake — Databricks Blog | 📄 Article | https://www.databricks.com/blog/delta-lake-vs-apache-iceberg |
| Apache Iceberg — The Definitive Guide (free PDF) | 📖 Book | https://iceberg.apache.org/docs/latest/books/ |
| Dremio: Open Table Format Comparison | 📄 Article | https://www.dremio.com/blog/open-table-formats-delta-lake-iceberg-and-hudi/ |
| Learning Spark 2nd Ed (Databricks — free) | 📖 Book | https://www.databricks.com/resources/ebook/learning-spark-lightning-fast-data-analytics |

---

## 1. The 30-Second Summary

```
Delta Lake:
  - Created by Databricks (2019), donated to Linux Foundation
  - Native format for Databricks platform
  - Best-in-class tooling on Databricks
  - Works outside Databricks (Spark, Flink, Trino)
  - Single-engine ACID via transaction log (_delta_log/)

Apache Iceberg:
  - Created at Netflix (2018), donated to Apache Foundation
  - Engine-agnostic by design — works equally well on Spark, Flink, Trino, Snowflake, etc.
  - Superior partition evolution (change partition strategy without rewriting data)
  - Hidden partitioning (no manual partition spec in queries)
  - Stronger multi-engine concurrent write support

When to choose:
  Databricks-first shop  → Delta Lake (deeper integration, Photon engine)
  Multi-cloud/multi-engine → Apache Iceberg (vendor-neutral, broader catalog support)
  AWS-native             → Iceberg (native in Athena, EMR, Glue)
  Streaming-heavy        → Both are good; Delta Lake slightly ahead for Spark Streaming
```

---

## 2. Architecture Deep Dive

### 2.1 Delta Lake Internals

```
table_path/
├── _delta_log/                     ← Transaction log (the brain)
│   ├── 00000000000000000000.json   ← Commit 0: CREATE TABLE
│   ├── 00000000000000000001.json   ← Commit 1: INSERT
│   ├── 00000000000000000002.json   ← Commit 2: UPDATE (MERGE)
│   ├── 00000000000000000010.checkpoint.parquet  ← Checkpoint every 10 commits
│   └── _last_checkpoint            ← Points to latest checkpoint
├── part-00000-abc123.parquet       ← Data files (Parquet)
├── part-00001-def456.parquet
└── ...

Transaction log entry (JSON):
{
  "commitInfo": {"timestamp": 1704067200000, "operation": "MERGE", "operationMetrics": {...}},
  "add":    [{"path": "part-new.parquet", "size": 102400, "stats": {...}}],
  "remove": [{"path": "part-old.parquet", "deletionTimestamp": 1704067200000}]
}

Key properties:
  - Optimistic concurrency: writers read latest log, attempt commit, retry on conflict
  - Checkpoint files: compact JSON logs every N commits (default: 10)
  - File-level statistics: min/max per column → enables data skipping
  - Z-ORDER: co-locate related data for multi-column skipping
```

### 2.2 Apache Iceberg Internals

```
table_path/
├── metadata/
│   ├── v1.metadata.json            ← Table metadata (schema, partitions, snapshots)
│   ├── v2.metadata.json            ← Updated after each write
│   ├── snap-123456.avro            ← Snapshot: list of manifest files
│   └── manifest-abc.avro           ← Manifest: list of data files + statistics
└── data/
    ├── category=Electronics/
    │   ├── 00000-0-abc.parquet
    │   └── 00001-0-def.parquet
    └── category=Clothing/
        └── 00000-0-ghi.parquet

Metadata hierarchy:
  Catalog
    └── Table
          └── Snapshot (each commit = new snapshot)
                └── Manifest List (one per snapshot)
                      └── Manifest File (N per snapshot, holds file stats)
                            └── Data Files (Parquet / ORC / Avro)

Key properties:
  - Three-layer metadata: table → snapshot → manifest → data files
  - Manifest files store column statistics (min/max/null count)
  - Snapshot isolation: each write creates a new snapshot (never modifies old ones)
  - Catalog abstraction: Hive Metastore, Glue, Nessie, REST, JDBC
```

### 2.3 Metadata Architecture Comparison

| Aspect | Delta Lake | Apache Iceberg |
|--------|-----------|----------------|
| Metadata format | JSON transaction log | Avro manifest files + JSON metadata |
| Concurrency model | Optimistic (log-based) | Optimistic (snapshot-based) |
| Conflict detection | File-level (column-level in some ops) | File-level |
| Multi-engine writes | Limited (Spark primary) | Strong (designed for it) |
| Catalog dependency | Optional (path-based works) | Required for full features |
| Small file stats | Per-file in log | Per-file in manifest |
| Checkpoint/compaction | Auto every 10 commits | Manual manifest rewrite |

---

## 3. ACID Transactions

Both Delta Lake and Iceberg provide full ACID guarantees, but through different mechanisms.

### 3.1 Delta Lake ACID

```python
from delta.tables import DeltaTable
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# MERGE (upsert) — atomic operation
delta_table = DeltaTable.forPath(spark, "/data/lake/silver/orders")

delta_table.alias("target").merge(
    updates.alias("source"),
    "target.id = source.id"
).whenMatchedUpdate(set={
    "status":     "source.status",
    "total":      "source.total",
    "updated_at": "source.updated_at",
}).whenNotMatchedInsert(values={
    "id":         "source.id",
    "status":     "source.status",
    "total":      "source.total",
    "created_at": "source.created_at",
    "updated_at": "source.updated_at",
}).execute()

# DELETE — atomic
delta_table.delete("status = 'cancelled' AND updated_at < '2023-01-01'")

# UPDATE — atomic
delta_table.update(
    condition="status = 'pending' AND created_at < '2024-01-01'",
    set={"status": "'expired'"}
)

# Transaction isolation — concurrent reads always see consistent snapshot
df1 = spark.read.format("delta").load("/data/lake/silver/orders")  # snapshot at T1
# ... another writer does a MERGE at T2 ...
df1.count()  # still reads snapshot from T1 — isolation guaranteed
```

### 3.2 Apache Iceberg ACID

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.iceberg.spark.SparkSessionCatalog") \
    .config("spark.sql.catalog.spark_catalog.type", "hive") \
    .getOrCreate()

# MERGE INTO (SQL syntax — identical semantics to Delta)
spark.sql("""
    MERGE INTO prod.db.orders AS target
    USING updates AS source
    ON target.id = source.id
    WHEN MATCHED THEN UPDATE SET
        target.status     = source.status,
        target.total      = source.total,
        target.updated_at = source.updated_at
    WHEN NOT MATCHED THEN INSERT *
""")

# DELETE
spark.sql("""
    DELETE FROM prod.db.orders
    WHERE status = 'cancelled' AND updated_at < '2023-01-01'
""")

# UPDATE
spark.sql("""
    UPDATE prod.db.orders
    SET status = 'expired'
    WHERE status = 'pending' AND created_at < '2024-01-01'
""")

# Row-level deletes with Iceberg v2 (position/equality deletes)
# Iceberg writes small "delete files" instead of rewriting data files
# This makes individual row deletes very fast
spark.sql("DELETE FROM prod.db.orders WHERE id = 12345")
# → Writes a small equality-delete file (no data file rewrite!)
```

---

## 4. Schema Evolution

This is one of Iceberg's strongest differentiators.

### 4.1 Delta Lake Schema Evolution

```python
# Option 1: mergeSchema — adds new columns
df_with_new_col.write \
    .format("delta") \
    .option("mergeSchema", "true") \
    .mode("append") \
    .save("/data/lake/orders")

# Option 2: overwriteSchema — replaces schema (dangerous!)
df_new_schema.write \
    .format("delta") \
    .option("overwriteSchema", "true") \
    .mode("overwrite") \
    .save("/data/lake/orders")

# Using SQL DDL
spark.sql("ALTER TABLE delta.`/data/lake/orders` ADD COLUMNS (discount DOUBLE)")
spark.sql("ALTER TABLE delta.`/data/lake/orders` RENAME COLUMN total TO total_amount")
spark.sql("ALTER TABLE delta.`/data/lake/orders` DROP COLUMN old_column")

# Limitations:
# ❌ Cannot widen types (INT → LONG) without table rewrite in older versions
# ❌ Cannot reorder columns without rewrite
# ✅ Can add nullable columns (safe, non-breaking)
# ✅ Can rename columns (Delta Lake 2.0+)
```

### 4.2 Apache Iceberg Schema Evolution

```python
# Iceberg tracks column IDs, not names — column renames are truly safe
# Old data files still readable with new schema

spark.sql("ALTER TABLE prod.db.orders ADD COLUMN discount DOUBLE")
spark.sql("ALTER TABLE prod.db.orders RENAME COLUMN total TO total_amount")
spark.sql("ALTER TABLE prod.db.orders DROP COLUMN old_column")

# TYPE WIDENING — Iceberg supports safe type promotions:
spark.sql("ALTER TABLE prod.db.orders ALTER COLUMN quantity TYPE BIGINT")
# INT → LONG: safe (no data rewrite needed)
# FLOAT → DOUBLE: safe
# DECIMAL(10,2) → DECIMAL(15,2): safe

# Column reordering
spark.sql("ALTER TABLE prod.db.orders ALTER COLUMN discount AFTER total_amount")

# Iceberg's secret: columns have INTERNAL IDs
# Old data: col 1="id", col 2="total", col 3="status"
# After rename: col 1="id", col 2="total_amount", col 3="status"
# Old files still readable — Iceberg maps by ID, not name!
```

### 4.3 Schema Evolution Comparison

| Feature | Delta Lake | Apache Iceberg |
|---------|-----------|----------------|
| Add nullable column | ✅ | ✅ |
| Add non-nullable column | ⚠️ Needs rewrite | ✅ (default value) |
| Rename column | ✅ (2.0+) | ✅ (always, by column ID) |
| Drop column | ✅ | ✅ |
| Reorder columns | ❌ Needs rewrite | ✅ |
| Widen types (INT→LONG) | ✅ (3.0+) | ✅ |
| Old files after rename | ✅ (column mapping) | ✅ (column ID mapping) |
| Struct field evolution | ✅ (limited) | ✅ (full) |

---

## 5. Partitioning — Iceberg's Biggest Win

This is where Iceberg clearly leads.

### 5.1 Delta Lake Partitioning

```python
# Delta Lake: physical partitioning — partition columns visible in directory names
df.write \
    .format("delta") \
    .partitionBy("year", "month") \
    .save("/data/lake/orders")

# Directory structure:
# orders/year=2024/month=01/part-0.parquet
# orders/year=2024/month=02/part-0.parquet

# PROBLEM 1: Queries must specify partition columns explicitly
spark.sql("""
    SELECT * FROM orders
    WHERE year = 2024 AND month = 1   -- ✅ uses partition
    -- vs
    WHERE created_at = '2024-01-15'   -- ❌ full scan! year/month not derived automatically
""")

# PROBLEM 2: Changing partition strategy requires FULL TABLE REWRITE
# If you partitioned by month and want to change to week:
# → Must rewrite ALL historical data

# PROBLEM 3: Partition values exposed to users
# Users must know the partition scheme to query efficiently
```

### 5.2 Apache Iceberg Partitioning

```python
# Iceberg: HIDDEN partitioning — users query on real columns
spark.sql("""
    CREATE TABLE prod.db.orders (
        id         INT,
        status     STRING,
        total      DOUBLE,
        created_at TIMESTAMP
    )
    USING iceberg
    PARTITIONED BY (
        months(created_at),    -- partition by month, derived from created_at
        truncate(10, status)   -- partition on first 10 chars of status
    )
""")

# Users query the real column, not the derived partition:
spark.sql("""
    SELECT * FROM prod.db.orders
    WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31'
    -- Iceberg automatically derives the partition filter: month(2024-01) 
    -- No need to write "WHERE year=2024 AND month=1"
""")

# PARTITION EVOLUTION — change strategy without rewriting data!
spark.sql("""
    ALTER TABLE prod.db.orders
    REPLACE PARTITION FIELD months(created_at)
    WITH days(created_at)
""")
# Old data: still partitioned by month
# New data: partitioned by day
# BOTH work correctly with the same query — no data rewrite!

# Iceberg partition transforms:
# years(ts)      → partition by year
# months(ts)     → partition by month
# days(ts)       → partition by day
# hours(ts)      → partition by hour
# bucket(N, col) → hash into N buckets
# truncate(N, s) → first N chars of string
# identity(col)  → standard value partitioning
```

### 5.3 Partitioning Comparison

| Feature | Delta Lake | Apache Iceberg |
|---------|-----------|----------------|
| Hidden partitioning | ❌ Manual spec required | ✅ Automatic predicate pushdown |
| Partition evolution | ❌ Full rewrite | ✅ Zero-copy, old data intact |
| Partition transforms | ❌ Manual (must compute year/month) | ✅ Built-in (months, days, hours, bucket) |
| Mixed-partition reads | ❌ Tricky | ✅ Seamless |
| Auto partition pruning | ✅ (if spec matches) | ✅ (always) |

---

## 6. Time Travel

Both support time travel, with slightly different syntax.

### 6.1 Delta Lake Time Travel

```python
# By version
spark.read.format("delta").option("versionAsOf", 5).load("/data/lake/orders")

# By timestamp
spark.read.format("delta").option("timestampAsOf", "2024-01-15 10:00:00").load("/data/lake/orders")

# SQL
spark.sql("SELECT * FROM delta.`/data/lake/orders` VERSION AS OF 5")
spark.sql("SELECT * FROM delta.`/data/lake/orders` TIMESTAMP AS OF '2024-01-15'")

# View history
from delta.tables import DeltaTable
dt = DeltaTable.forPath(spark, "/data/lake/orders")
dt.history(10).show(truncate=False)

# Restore to a previous version
dt.restoreToVersion(3)
dt.restoreToTimestamp("2024-01-01 00:00:00")

# VACUUM: clean up old files (retention: 7 days default)
dt.vacuum(retentionHours=168)
```

### 6.2 Iceberg Time Travel

```python
# By snapshot ID
spark.read.option("snapshot-id", "8954274912598751442").table("prod.db.orders")

# By timestamp
spark.read.option("as-of-timestamp", "1704067200000").table("prod.db.orders")  # milliseconds!

# SQL (cleaner syntax)
spark.sql("""
    SELECT * FROM prod.db.orders
    FOR SYSTEM_TIME AS OF '2024-01-15 10:00:00'
""")
spark.sql("""
    SELECT * FROM prod.db.orders
    FOR SYSTEM_VERSION AS OF 8954274912598751442
""")

# View snapshots
spark.sql("SELECT * FROM prod.db.orders.snapshots").show()
spark.sql("SELECT * FROM prod.db.orders.history").show()

# View manifests (Iceberg-specific deep inspection)
spark.sql("SELECT * FROM prod.db.orders.manifests").show()
spark.sql("SELECT * FROM prod.db.orders.files").show()   # all data files

# Rollback to snapshot
spark.sql("""
    CALL prod.system.rollback_to_snapshot('db.orders', 8954274912598751442)
""")

# Expire old snapshots (cleanup)
spark.sql("""
    CALL prod.system.expire_snapshots(
        table => 'db.orders',
        older_than => TIMESTAMP '2024-01-01 00:00:00',
        retain_last => 10
    )
""")
```

---

## 7. Performance Optimization

### 7.1 Delta Lake Performance Features

```python
# Z-ORDER: co-locate related data for multi-column queries
spark.sql("""
    OPTIMIZE delta.`/data/lake/orders`
    ZORDER BY (customer_id, created_at)
""")
# After Z-ORDER: queries filtering on customer_id AND created_at
# read far fewer files (data skipping)

# File compaction (combine small files into large ones)
spark.sql("OPTIMIZE delta.`/data/lake/orders`")

# Predictive I/O (Databricks only): ML-based prefetching
# Auto-optimize (Databricks only): automatic compaction + Z-ORDER

# Bloom filter index (Delta Lake 2.0+)
spark.sql("""
    CREATE BLOOMFILTER INDEX ON TABLE delta.`/data/lake/orders`
    FOR COLUMNS (customer_id OPTIONS (fpp=0.1, numItems=50000000))
""")

# Column statistics: min/max/null count per file
# Used automatically for data skipping
# Check statistics:
from delta.tables import DeltaTable
dt = DeltaTable.forPath(spark, "/data/lake/orders")
dt.detail().show()
```

### 7.2 Iceberg Performance Features

```python
# File compaction (bin-pack: combine small files)
spark.sql("""
    CALL prod.system.rewrite_data_files(
        table => 'db.orders',
        strategy => 'binpack',
        options => map('target-file-size-bytes', '134217728')  -- 128 MB
    )
""")

# Sort-based compaction (like Z-ORDER)
spark.sql("""
    CALL prod.system.rewrite_data_files(
        table => 'db.orders',
        strategy => 'sort',
        sort_order => 'customer_id ASC NULLS LAST, created_at DESC NULLS LAST'
    )
""")

# Z-ORDER equivalent (Iceberg terminology: space-filling curve)
spark.sql("""
    CALL prod.system.rewrite_data_files(
        table => 'db.orders',
        strategy => 'sort',
        sort_order => 'zorder(customer_id, created_at)'
    )
""")

# Manifest rewrite (compact manifests for faster planning)
spark.sql("""
    CALL prod.system.rewrite_manifests('db.orders')
""")

# Column statistics for data skipping (auto-collected)
spark.sql("SELECT * FROM prod.db.orders.files").select(
    "file_path", "record_count",
    "lower_bounds", "upper_bounds", "null_value_counts"
).show()
```

### 7.3 Performance Comparison

| Feature | Delta Lake | Apache Iceberg |
|---------|-----------|----------------|
| File compaction | ✅ `OPTIMIZE` | ✅ `rewrite_data_files` |
| Multi-column sorting | ✅ Z-ORDER | ✅ Sort / Z-ORDER |
| Bloom filters | ✅ (2.0+) | ✅ |
| Column statistics | ✅ Auto | ✅ Auto |
| Manifest compaction | ✅ Checkpoint | ✅ `rewrite_manifests` |
| Photon engine (10x) | ✅ Databricks only | ❌ |
| Predictive I/O | ✅ Databricks only | ❌ |
| Liquid Clustering | ✅ Databricks only | ❌ (use sort) |

---

## 8. Multi-Engine Support (Critical Decision Factor)

### 8.1 Delta Lake Engine Support

```
✅  PySpark (Spark)       — native, best performance
✅  Spark SQL             — native
✅  Flink                 — delta-flink connector (read/write)
✅  Trino / Presto        — delta connector (read-only in some versions)
✅  Hive                  — limited support
✅  DuckDB                — via delta-rs (read-only)
✅  Pandas / Polars       — via delta-rs (read + write)
⚠️  Snowflake             — Iceberg export supported, not Delta directly
⚠️  BigQuery              — Iceberg supported, not Delta
⚠️  Athena                — Iceberg supported, Delta via manifest (workaround)
❌  Redshift Spectrum      — Iceberg supported, not Delta
```

```python
# Delta Lake with Pandas (via delta-rs — no Spark needed!)
# pip install deltalake
import deltalake as dl
import pandas as pd

# Write
dl.write_deltalake("/data/lake/orders", pd.DataFrame(data))

# Read
df = dl.DeltaTable("/data/lake/orders").to_pandas()

# DuckDB reading Delta directly
import duckdb
duckdb.sql("SELECT * FROM delta_scan('/data/lake/orders/')")
```

### 8.2 Iceberg Engine Support

```
✅  PySpark (Spark)       — native, full support
✅  Spark SQL             — native
✅  Flink                 — native (best streaming story)
✅  Trino                 — native, full support (excellent)
✅  Presto                — native
✅  Hive                  — native
✅  DuckDB                — Iceberg extension (read)
✅  Snowflake             — native Iceberg tables (GA)
✅  BigQuery              — native Iceberg tables (GA)
✅  Athena                — native Iceberg (v2)
✅  Redshift              — Iceberg support (2024)
✅  Dremio                — native (Dremio's primary format)
✅  StarRocks             — native
✅  Doris                 — native
✅  PyIceberg             — pure Python read/write (no Spark!)
```

```python
# PyIceberg — read/write Iceberg tables WITHOUT Spark
# pip install pyiceberg[s3,hive,pyarrow]
from pyiceberg.catalog import load_catalog
import pyarrow as pa

catalog = load_catalog("glue", **{
    "type": "glue",
    "s3.region": "us-east-1",
})

# Read
table = catalog.load_table("ecommerce.orders")
df = table.scan(
    row_filter="status = 'completed' AND total > 100",
    selected_fields=("id", "customer_id", "total"),
    limit=1000,
).to_arrow()

# Write
catalog.create_table(
    "ecommerce.orders_v2",
    schema=pa.schema([
        pa.field("id", pa.int64()),
        pa.field("total", pa.float64()),
    ])
)
table = catalog.load_table("ecommerce.orders_v2")
table.append(pa.table({"id": [1,2,3], "total": [100.0, 200.0, 300.0]}))

# Iceberg + DuckDB
import duckdb
duckdb.sql("INSTALL iceberg; LOAD iceberg;")
duckdb.sql("SELECT * FROM iceberg_scan('s3://bucket/iceberg/orders')")
```

---

## 9. Catalog Integration

### 9.1 Delta Lake Catalogs

```python
# 1. Path-based (simplest, no catalog needed)
spark.read.format("delta").load("/data/lake/orders")
spark.sql("SELECT * FROM delta.`/data/lake/orders`")

# 2. Hive Metastore
spark.sql("""
    CREATE TABLE orders
    USING DELTA
    LOCATION '/data/lake/orders'
""")
spark.sql("SELECT * FROM orders")

# 3. Unity Catalog (Databricks)
# 3-level namespace: catalog.schema.table
spark.sql("""
    CREATE TABLE main.ecommerce.orders
    USING DELTA
    LOCATION 's3://bucket/main/ecommerce/orders'
""")

# 4. Delta Sharing (share tables across organizations)
# (Databricks proprietary)
```

### 9.2 Iceberg Catalogs

```python
# Iceberg REQUIRES a catalog for full functionality
# Multiple options — choose based on your cloud/stack:

# 1. Apache Hive Metastore
spark.conf.set("spark.sql.catalog.hive_prod", "org.apache.iceberg.spark.SparkCatalog")
spark.conf.set("spark.sql.catalog.hive_prod.type", "hive")
spark.conf.set("spark.sql.catalog.hive_prod.uri", "thrift://localhost:9083")

# 2. AWS Glue Data Catalog
spark.conf.set("spark.sql.catalog.glue_prod", "org.apache.iceberg.spark.SparkCatalog")
spark.conf.set("spark.sql.catalog.glue_prod.catalog-impl",
               "org.apache.iceberg.aws.glue.GlueCatalog")
spark.conf.set("spark.sql.catalog.glue_prod.warehouse", "s3://my-bucket/warehouse")
spark.conf.set("spark.sql.catalog.glue_prod.io-impl",
               "org.apache.iceberg.aws.s3.S3FileIO")

# 3. Project Nessie (Git-like versioning for data!)
spark.conf.set("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog")
spark.conf.set("spark.sql.catalog.nessie.catalog-impl",
               "org.projectnessie.iceberg.NessieCatalog")
spark.conf.set("spark.sql.catalog.nessie.uri", "http://localhost:19120/api/v1")
spark.conf.set("spark.sql.catalog.nessie.ref", "main")

# Nessie: Git for data!
# Create a branch, test pipeline changes, merge to main
spark.sql("CREATE BRANCH dev IN nessie FROM main")
spark.sql("USE REFERENCE dev IN nessie")
spark.sql("INSERT INTO nessie.db.orders VALUES ...")  # only visible on dev branch
spark.sql("MERGE BRANCH dev INTO main IN nessie")     # promote to production

# 4. REST Catalog (universal — works with Gravitino, Polaris, Tabular)
spark.conf.set("spark.sql.catalog.rest", "org.apache.iceberg.spark.SparkCatalog")
spark.conf.set("spark.sql.catalog.rest.type", "rest")
spark.conf.set("spark.sql.catalog.rest.uri", "http://catalog-server:8181")

# 5. JDBC Catalog (PostgreSQL-backed metadata)
spark.conf.set("spark.sql.catalog.jdbc_prod", "org.apache.iceberg.spark.SparkCatalog")
spark.conf.set("spark.sql.catalog.jdbc_prod.catalog-impl",
               "org.apache.iceberg.jdbc.JdbcCatalog")
spark.conf.set("spark.sql.catalog.jdbc_prod.uri",
               "jdbc:postgresql://localhost:5432/iceberg_catalog")
```

### 9.3 Catalog Comparison

| Catalog | Delta Lake | Apache Iceberg |
|---------|-----------|----------------|
| Path-based (no catalog) | ✅ | ⚠️ Limited |
| Hive Metastore | ✅ | ✅ |
| AWS Glue | ✅ (via Spark) | ✅ Native |
| Unity Catalog | ✅ Native | ✅ (Databricks supports both) |
| Apache Polaris | ❌ | ✅ |
| Project Nessie | ❌ | ✅ (Git-like branching!) |
| Snowflake Open Catalog | ❌ | ✅ |
| REST Catalog (universal) | ❌ | ✅ |

---

## 10. Streaming Support

### 10.1 Delta Lake Streaming

```python
# Delta Lake + Spark Structured Streaming: excellent integration

# Read stream from Delta table (source)
stream = spark.readStream \
    .format("delta") \
    .load("/data/lake/bronze/orders")

# Write stream to Delta table (sink)
query = stream \
    .writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/checkpoints/orders") \
    .trigger(processingTime="30 seconds") \
    .start("/data/lake/silver/orders")

# Change Data Feed (CDF) — stream only changed rows
spark.conf.set(
    "spark.databricks.delta.properties.defaults.enableChangeDataFeed", "true"
)

changes = spark.readStream \
    .format("delta") \
    .option("readChangeFeed", "true") \
    .option("startingVersion", 0) \
    .load("/data/lake/silver/orders")
# Returns: _change_type (insert/update_preimage/update_postimage/delete), _commit_version
```

### 10.2 Iceberg Streaming

```python
# Iceberg + Flink: best-in-class streaming integration

# (Flink Java/Python API)
# Writing to Iceberg from Flink:
table_env.execute_sql("""
    CREATE TABLE orders_sink (
        id         INT,
        status     STRING,
        total      DOUBLE,
        created_at TIMESTAMP(6)
    ) WITH (
        'connector' = 'iceberg',
        'catalog-name' = 'hive_prod',
        'database-name' = 'ecommerce',
        'table-name' = 'orders',
        'write.upsert.enabled' = 'true'
    )
""")

# Iceberg + Spark Streaming (also supported)
query = spark.readStream \
    .format("iceberg") \
    .load("prod.ecommerce.orders") \
    .writeStream \
    .format("iceberg") \
    .outputMode("append") \
    .option("checkpointLocation", "/checkpoints/iceberg_orders") \
    .trigger(processingTime="1 minute") \
    .toTable("prod.ecommerce.orders_silver")
```

### 10.3 Streaming Comparison

| Feature | Delta Lake | Apache Iceberg |
|---------|-----------|----------------|
| Spark Structured Streaming | ✅ Excellent | ✅ Good |
| Apache Flink | ✅ Good | ✅ **Best-in-class** |
| Change Data Feed / CDC | ✅ Native | ✅ (Incremental scans) |
| Exactly-once writes | ✅ | ✅ |
| Streaming source (read) | ✅ | ✅ |

---

## 11. Concurrency & Multi-Writer Support

```
Scenario: 10 writers concurrently writing to the same table.

Delta Lake (Optimistic Concurrency Control):
  - Writer reads latest version → writes new files → attempts to commit to _delta_log
  - If another writer committed in the meantime → retry (conflict detection)
  - Conflict detection: at the transaction level
  - Works well for Spark-to-Spark; multi-engine writes need care

Apache Iceberg (Snapshot Isolation):
  - Writer reads current snapshot → writes new files → atomically swaps to new snapshot
  - Each snapshot is immutable — no conflicts between reads and writes
  - Better designed for multi-engine writes (Spark + Flink + Trino simultaneously)
  - Row-level operations use "delete files" to avoid rewriting data

Key difference:
  Delta Lake: conflict at commit time (may need to retry)
  Iceberg:    each writer creates independent snapshot; catalog serializes commits
```

---

## 12. Databricks Platform vs Open Ecosystem

### 12.1 Databricks (Commercial Platform)

```
What Databricks adds on top of Delta Lake:
┌────────────────────────────────────────────────────────┐
│ DATABRICKS PLATFORM                                     │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Photon      │  │  Unity       │  │  Delta Live  │  │
│  │  Engine      │  │  Catalog     │  │  Tables      │  │
│  │  (10x faster)│  │  (governance)│  │  (DLT)       │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Liquid      │  │  Predictive  │  │  MLflow +    │  │
│  │  Clustering  │  │  I/O         │  │  Feature     │  │
│  │  (auto sort) │  │  (ML prefetch│  │  Store       │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Auto       │  │  Delta       │  │  Notebooks + │  │
│  │  Optimize   │  │  Sharing     │  │  Workflows   │  │
│  │  (compaction│  │  (cross-org  │  │  (Airflow    │  │
│  │  + ZORDER)  │  │  sharing)    │  │  alternative)│  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  Underlying format: Delta Lake (open source)            │
└────────────────────────────────────────────────────────┘
```

### 12.2 Databricks-Specific Features (Not Available Elsewhere)

```python
# 1. Liquid Clustering (replaces ZORDER — smarter, online)
spark.sql("""
    CREATE TABLE orders (
        id INT, customer_id INT, status STRING, created_at TIMESTAMP
    )
    USING DELTA
    CLUSTER BY (customer_id, status)   -- automatically maintained
""")
# No manual OPTIMIZE + ZORDER needed — Databricks handles it online

# 2. Delta Live Tables (DLT) — declarative ETL
# (Only in Databricks Workflows)
import dlt
from pyspark.sql.functions import col

@dlt.table(
    name="silver_orders",
    comment="Cleaned orders from bronze",
    table_properties={"pipelines.autoOptimize.zOrderCols": "customer_id,created_at"},
)
@dlt.expect_or_drop("valid_total", "total >= 0")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def silver_orders():
    return dlt.read("bronze_orders") \
        .filter(col("status").isin("pending","completed","cancelled","refunded")) \
        .withColumn("status", col("status").cast("string"))

# DLT manages: schema evolution, data quality, lineage, retries, backfills

# 3. Unity Catalog — fine-grained governance
spark.sql("""
    GRANT SELECT ON TABLE main.ecommerce.orders TO `data-analysts@company.com`
""")
spark.sql("""
    CREATE MASK FUNCTION mask_email(val STRING)
    RETURNS STRING
    RETURN CASE WHEN is_member('pii-team') THEN val ELSE regexp_replace(val, '(.).*@', '$1***@') END
""")
spark.sql("""
    ALTER TABLE main.ecommerce.customers
    ALTER COLUMN email SET MASK mask_email
""")
```

### 12.3 Open Iceberg Ecosystem

```python
# Iceberg equivalent: open, works everywhere

# Polaris Catalog (Snowflake open-sourced, 2024) — governance
# Gravitino (Apache project) — open catalog + governance
# Project Nessie — Git-like data versioning

# Example: branch-based data development with Nessie
# (like Git, but for tables)
from pynessie import init

client = init()
# Create a feature branch
client.create_branch("feature/new-partitioning", "main")

# Work on the branch
spark.conf.set("spark.sql.catalog.nessie.ref", "feature/new-partitioning")
spark.sql("ALTER TABLE nessie.db.orders REPLACE PARTITION FIELD months(ts) WITH days(ts)")
# → Only visible on this branch

# Validate, then merge
client.merge("feature/new-partitioning", "main")
```

---

## 13. Cloud Provider Native Support

| Cloud | Delta Lake | Apache Iceberg |
|-------|-----------|----------------|
| **AWS** | Via Spark on EMR, Glue | ✅ Athena (native), EMR, Glue native, Lake Formation |
| **Azure** | ✅ Azure Databricks, Synapse | Synapse (limited), Fabric |
| **GCP** | Via Dataproc | ✅ BigQuery native Iceberg tables (GA) |
| **Snowflake** | ❌ No native support | ✅ Native Iceberg tables (GA) |
| **Databricks** | ✅ Native (home turf) | ✅ Also supported on Databricks |

---

## 14. Full Side-by-Side Decision Matrix

| Dimension | Delta Lake | Apache Iceberg | Winner |
|-----------|-----------|----------------|--------|
| **Databricks ecosystem** | ✅ Native | ✅ Supported | Delta (deeper integration) |
| **Multi-engine writes** | ⚠️ Primarily Spark | ✅ Designed for it | Iceberg |
| **Snowflake / BigQuery / Athena** | ❌ | ✅ Native | Iceberg |
| **Partition evolution** | ❌ Full rewrite | ✅ Zero-copy | Iceberg |
| **Hidden partitioning** | ❌ | ✅ | Iceberg |
| **Schema evolution** | ✅ Good | ✅ Better (column IDs) | Iceberg |
| **Time travel** | ✅ | ✅ | Tie |
| **Flink streaming** | ✅ Good | ✅ Best-in-class | Iceberg |
| **Spark streaming** | ✅ Best-in-class | ✅ Good | Delta |
| **Change Data Feed** | ✅ Native | ✅ (Incremental scans) | Delta |
| **Catalog options** | Limited | ✅ 6+ catalogs | Iceberg |
| **Git-like branching** | ❌ | ✅ (Nessie) | Iceberg |
| **Python without Spark** | ✅ delta-rs | ✅ PyIceberg | Tie |
| **DuckDB integration** | ✅ delta_scan() | ✅ iceberg_scan() | Tie |
| **Governance / ACL** | ✅ Unity Catalog | ✅ Polaris, Gravitino | Tie |
| **Performance on Databricks** | ✅ Photon + Liquid | Good | Delta |
| **Vendor lock-in** | ⚠️ Databricks-centric | ✅ Truly vendor-neutral | Iceberg |
| **Community size** | Large (Databricks) | Large (Apache) | Tie |
| **AWS-first architecture** | Workarounds needed | ✅ Native everywhere | Iceberg |

---

## 15. When to Choose What

```
Choose DELTA LAKE if:
  ✅ You are building primarily on Databricks
  ✅ You want Photon engine (10x query speedup)
  ✅ You use Delta Live Tables (DLT) for declarative ETL
  ✅ You need Liquid Clustering (auto-sort, no manual OPTIMIZE)
  ✅ You need Change Data Feed for Spark Streaming
  ✅ Your team is already Databricks-skilled
  ✅ You need Unity Catalog for fine-grained data governance

Choose APACHE ICEBERG if:
  ✅ You need true engine-agnostic: Spark + Flink + Trino + Snowflake + Athena
  ✅ You are on AWS (Athena, EMR, Glue — Iceberg is first-class)
  ✅ You need Snowflake or BigQuery to read the same tables
  ✅ Your partition strategy may change over time (partition evolution)
  ✅ You have multiple teams writing concurrently from different engines
  ✅ You want Git-like branch-based data development (Nessie)
  ✅ You need to avoid vendor lock-in
  ✅ You are building a Flink-first streaming platform

You DON'T need to choose — use BOTH if:
  ✅ Databricks (Delta) for Spark batch + streaming
  ✅ Iceberg for Snowflake/Athena consumption
  ✅ Databricks natively supports reading Iceberg tables
  ✅ Use UniForm (Delta Lake 3.0): write Delta, also readable as Iceberg
```

---

## 16. UniForm — Delta + Iceberg Interoperability

Delta Lake 3.0 introduced **UniForm**: write once as Delta, read as Iceberg or Hudi.

```python
# Create a Delta table with UniForm enabled
spark.sql("""
    CREATE TABLE orders (
        id INT, status STRING, total DOUBLE
    )
    USING DELTA
    TBLPROPERTIES (
        'delta.universalFormat.enabledFormats' = 'iceberg'
    )
""")

# Or enable on existing table
spark.sql("""
    ALTER TABLE orders
    SET TBLPROPERTIES ('delta.universalFormat.enabledFormats' = 'iceberg')
""")

# Now the same table is readable as:
# Delta:   spark.read.format("delta").load(...)
# Iceberg: spark.read.format("iceberg").load(...)
# Athena:  SELECT * FROM iceberg.db.orders  (via Glue Catalog)
# Trino:   SELECT * FROM iceberg.db.orders

# UniForm makes the "choose one" decision less critical
# → Write Delta on Databricks, consume via Iceberg anywhere
```

---

## 17. Practical Code: Same Pipeline in Both

### Delta Lake Pipeline

```python
from delta import configure_spark_with_delta_pip
from delta.tables import DeltaTable
from pyspark.sql import SparkSession, functions as F

spark = configure_spark_with_delta_pip(
    SparkSession.builder
    .appName("Delta Pipeline")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog")
).getOrCreate()

SILVER = "/data/lake/silver/orders"

# Read new data
new_orders = spark.read.parquet("/data/lake/bronze/orders/2024/01/15/")

# Clean
clean = new_orders \
    .filter(F.col("id").isNotNull() & (F.col("total") >= 0)) \
    .withColumn("status", F.lower(F.trim(F.col("status")))) \
    .withColumn("_silver_at", F.current_timestamp())

# Merge into Silver
if DeltaTable.isDeltaTable(spark, SILVER):
    DeltaTable.forPath(spark, SILVER).alias("t").merge(
        clean.alias("s"), "t.id = s.id"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    clean.write.format("delta").save(SILVER)

# Optimize
spark.sql(f"OPTIMIZE delta.`{SILVER}` ZORDER BY (customer_id, created_at)")
```

### Apache Iceberg Pipeline

```python
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("Iceberg Pipeline") \
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.prod", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.prod.type", "hive") \
    .getOrCreate()

# Read new data
new_orders = spark.read.parquet("/data/lake/bronze/orders/2024/01/15/")

# Clean
clean = new_orders \
    .filter(F.col("id").isNotNull() & (F.col("total") >= 0)) \
    .withColumn("status", F.lower(F.trim(F.col("status")))) \
    .withColumn("_silver_at", F.current_timestamp())

clean.createOrReplaceTempView("clean_orders")

# Merge into Iceberg Silver
spark.sql("""
    MERGE INTO prod.ecommerce.orders AS t
    USING clean_orders AS s
    ON t.id = s.id
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
""")

# Compact + re-sort
spark.sql("""
    CALL prod.system.rewrite_data_files(
        table => 'ecommerce.orders',
        strategy => 'sort',
        sort_order => 'zorder(customer_id, created_at)'
    )
""")
```

---

## 18. Quick Reference Cheat Sheet

```
┌──────────────────────────────────────────────────────────────────┐
│              DELTA LAKE vs APACHE ICEBERG — QUICK REF            │
├──────────────────────┬───────────────────┬───────────────────────┤
│ Feature              │ Delta Lake        │ Apache Iceberg        │
├──────────────────────┼───────────────────┼───────────────────────┤
│ Created by           │ Databricks (2019) │ Netflix (2018)        │
│ Governed by          │ Linux Foundation  │ Apache Foundation     │
│ Table format file    │ _delta_log/*.json │ metadata/*.avro+json  │
│ Time travel          │ VERSION/TIMESTAMP │ SYSTEM_TIME/VERSION   │
│ MERGE syntax         │ DeltaTable.merge()│ MERGE INTO (SQL)      │
│ Partition evolution  │ Rewrite needed    │ ALTER PARTITION FIELD │
│ Hidden partitioning  │ No                │ Yes                   │
│ Schema by column ID  │ Partial (2.0+)    │ Always                │
│ Python without Spark │ delta-rs          │ PyIceberg             │
│ Flink support        │ Good              │ Excellent             │
│ Snowflake native     │ No                │ Yes (GA)              │
│ Athena native        │ Workaround        │ Yes (native)          │
│ Nessie branching     │ No                │ Yes                   │
│ DuckDB               │ delta_scan()      │ iceberg_scan()        │
│ Both from one table  │ UniForm (3.0+)    │ -                     │
│ Best platform        │ Databricks        │ AWS / multi-cloud     │
└──────────────────────┴───────────────────┴───────────────────────┘
```

---

## 19. Apache Hudi — The Third Table Format

No complete comparison is production-grade without mentioning **Apache Hudi** (Hadoop Upserts Deletes and Incrementals), created at Uber in 2016.

### Hudi Key Concepts

```
Hudi table types:
  Copy-On-Write (COW): rewrites Parquet files on every write
                       → Fast reads, slow writes
                       → Like Delta Lake and Iceberg default

  Merge-On-Read (MOR): writes small delta log files, merges lazily on read
                       → Fast writes, slightly slower reads (compaction needed)
                       → Unique to Hudi — great for high-frequency CDC

Hudi record key: every record needs a primary key (like a DB table)
Hudi partition: standard partition-by-column approach (like Delta)
```

```python
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder     .appName("HudiWrite")     .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")     .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.hudi.catalog.HoodieCatalog")     .getOrCreate()

# Write to Hudi (MOR table — fast writes, good for CDC)
hudi_options = {
    "hoodie.table.name": "orders",
    "hoodie.datasource.write.recordkey.field": "id",
    "hoodie.datasource.write.partitionpath.field": "country",
    "hoodie.datasource.write.table.type": "MERGE_ON_READ",
    "hoodie.datasource.write.operation": "upsert",
    "hoodie.datasource.write.precombine.field": "updated_at",
    # Compaction (merge log files into Parquet periodically)
    "hoodie.compact.inline": "false",          # run compaction async
    "hoodie.compact.inline.max.delta.commits": "5",
    # Cleaner (remove old file versions)
    "hoodie.cleaner.commits.retained": "10",
}

df.write     .format("hudi")     .options(**hudi_options)     .mode("append")     .save("s3://bucket/hudi/orders/")

# Read (always reads latest snapshot)
spark.read.format("hudi").load("s3://bucket/hudi/orders/").show()

# Incremental read (only records changed since a commit)
spark.read.format("hudi")     .option("hoodie.datasource.query.type", "incremental")     .option("hoodie.datasource.read.begin.instanttime", "20240101000000")     .load("s3://bucket/hudi/orders/")     .show()

# Time travel
spark.read.format("hudi")     .option("as.of.instant", "20240115120000")     .load("s3://bucket/hudi/orders/")     .show()
```

### Three-Way Comparison: Delta Lake vs Iceberg vs Hudi

| Feature | Delta Lake | Apache Iceberg | Apache Hudi |
|---------|-----------|----------------|-------------|
| Created by | Databricks | Netflix | Uber |
| Table types | COW only | COW only | COW + **MOR** |
| Fast high-freq writes | Moderate | Moderate | **Best** (MOR) |
| Partition evolution | ❌ Rewrite | ✅ Zero-copy | ❌ Rewrite |
| Hidden partitioning | ❌ | ✅ | ❌ |
| Schema evolution | ✅ Good | ✅ Best | ✅ Good |
| Time travel | ✅ | ✅ | ✅ |
| CDC / incremental read | ✅ CDF | ✅ Incremental scan | **✅ Native incremental** |
| Multi-engine support | Moderate | ✅ Best | Moderate |
| Snowflake native | ❌ | ✅ | ❌ |
| Compaction needed | No | No | Yes (MOR) |
| Primary key required | No | No | **Yes** |
| AWS Athena native | No | ✅ | Workaround |
| Flink streaming | Good | **Best** | Good |
| Best for | Databricks shops | Multi-engine / cloud | High-freq CDC / Uber-scale |

### When to Choose Hudi

```
Choose Apache Hudi if:
  ✅ Very high write frequency (10M+ upserts/hour)
  ✅ You need native incremental CDC reads (MOR streaming source)
  ✅ You are on AWS EMR (AWS has strong Hudi support)
  ✅ Your records always have a primary key
  ✅ You are coming from a Hudi-using organisation (Uber, Robinhood, etc.)
  ✅ You need COW → MOR flexibility per table

Do NOT choose Hudi if:
  ❌ You need Snowflake or BigQuery native reads
  ❌ You need hidden partitioning or partition evolution
  ❌ Your records do not have stable primary keys
  ❌ You are Databricks-first (Delta is better integrated)
```

---

## 20. Apache Paimon (Emerging Format — Worth Knowing)

Apache Paimon (originally Flink Table Store) is designed for **streaming-first** data lakes
with Flink as the primary write engine.

```
Key differentiators:
  - Native Flink table format (best-in-class Flink integration)
  - Streaming upserts with sub-minute latency (better than Iceberg + Flink)
  - Lookup tables: fast key-value lookups from Flink streaming jobs
  - Level-based LSM (Log-Structured Merge Tree) storage for fast writes
  - Full CDC support natively

Best for:
  - Flink-native streaming pipelines
  - Real-time data lakes (latency < 1 minute)
  - Organisations already deep in Flink (Alibaba, ByteDance, etc.)

Not yet production-ready for:
  - Multi-engine reads (Spark/Trino support is newer and less stable)
  - Snowflake or BigQuery native reads (not supported)
```

### Updated Decision Matrix (All Four Formats)

```
Choose DELTA LAKE if:   Databricks + Photon + Unity Catalog
Choose ICEBERG if:      Multi-cloud, Snowflake/Athena, partition evolution
Choose HUDI if:         High-frequency CDC, MOR tables, AWS EMR
Choose PAIMON if:       Flink-native streaming, sub-minute latency

If in doubt and starting fresh: Apache Iceberg is the safest vendor-neutral choice.
```

---

## 🏋️ Exercises

### Exercise 1 — Delta Lake Time Travel Audit
Create a Delta table, run 5 write operations, then:
- Query each historical version
- Compute the diff between version 2 and version 5
- Restore to version 3 and verify
- Run VACUUM and confirm older versions are gone

### Exercise 2 — Iceberg Partition Evolution
Create an Iceberg table partitioned by `months(created_at)`.
Insert 1 year of data. Then:
- Change partition to `days(created_at)` with `ALTER PARTITION FIELD`
- Insert new data
- Verify old data is still readable with the same query
- Inspect `prod.db.orders.partitions` to see mixed partition specs

### Exercise 3 — Multi-Engine Read
1. Write a table as Delta (with UniForm enabled)
2. Read it via Spark as Delta
3. Read it via DuckDB as `delta_scan()`
4. Read it via PyIceberg
5. Compare row counts — all three should match

### Exercise 4 — Nessie Branch Workflow
1. Set up Project Nessie (via Docker)
2. Create a production Iceberg table on `main` branch
3. Create a `dev` branch, run a schema change + data migration
4. Validate on `dev` branch without affecting `main`
5. Merge `dev` into `main`

---

## ✅ Self-Check Questions

1. What is the fundamental metadata structure difference between Delta Lake and Iceberg?
2. What is hidden partitioning in Iceberg and why does it matter?
3. What is partition evolution and can Delta Lake do it?
4. What does UniForm (Delta Lake 3.0) enable?
5. Which format has better multi-engine concurrent write support, and why?
6. What is the difference between a Delta Lake checkpoint and an Iceberg manifest rewrite?
7. When would you choose Iceberg over Delta Lake on AWS?
8. What is Project Nessie and what Git concept does it bring to data lakes?
9. What is PyIceberg and when would you use it over PySpark?
10. What are Iceberg's row-level delete files and why are they faster than Delta's approach?

---

## 🔗 Key Links

- https://delta.io/ — Delta Lake home
- https://iceberg.apache.org/ — Apache Iceberg home
- https://docs.delta.io/latest/index.html — Delta Lake docs
- https://iceberg.apache.org/docs/latest/ — Iceberg docs
- https://iceberg.apache.org/docs/latest/books/ — The Definitive Guide (free)
- https://projectnessie.org/ — Nessie (Git for data)
- https://py.iceberg.apache.org/ — PyIceberg docs
- https://github.com/delta-io/delta-rs — Delta Lake in Python/Rust
- https://www.dremio.com/blog/open-table-formats-delta-lake-iceberg-and-hudi/ — 3-way comparison
