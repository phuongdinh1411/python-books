# Pillar 8 — Large-Scale Data Processing

> **Duration:** 1 week | **Priority:** 🟡 Medium-High

---

## 🎯 Learning Objectives

- Design data lakes with proper organization and partitioning
- Use Delta Lake for ACID transactions on data lakes
- Implement CDC (Change Data Capture) with Debezium
- Handle data quality at scale: schema enforcement, deduplication, reconciliation
- Design for scalability: horizontal sharding, partition strategies
- Understand data lineage and observability

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [Delta Lake Docs](https://docs.delta.io/) | 📄 Docs | ✅ Free |
| [Debezium Docs](https://debezium.io/documentation/reference/stable/) | 📄 Docs | ✅ Free |
| [Great Expectations Docs](https://greatexpectations.io/) | 📄 Docs | ✅ Free |
| [The Data Engineering Cookbook — GitHub](https://github.com/andkret/Cookbook) | 📄 Free PDF | ✅ Free |
| [Martin Kleppmann — Lecture notes (YouTube)](https://www.youtube.com/playlist?list=PLeKd45zvjcDFUEv_ohr_HdUFe97RItdiB) | 🎥 Video | ✅ Free (covers DDIA topics) |
| [Databricks Delta Lake blog](https://www.databricks.com/blog/2019/08/14/productionizing-machine-learning-with-delta-lake.html) | 📄 Article | ✅ Free |

> 💡 **Optional paid book:** *Designing Data-Intensive Applications* Ch 10–12 — Martin Kleppmann (O'Reilly)

---

## Section 1 — Data Lake Architecture

```
Bronze / Raw Layer    → exact copy of source data, never modified
Silver / Clean Layer  → validated, deduplicated, typed, partitioned
Gold / Serving Layer  → business-ready aggregates, star schema tables

                Bronze                Silver              Gold
Source ──────→ raw/           ──────→ clean/     ──────→ marts/
  DB               orders/              orders/              fct_orders/
  API              events/              events/              dim_customers/
  Files            customers/           customers/           revenue_daily/
                (raw Parquet,       (validated,         (pre-aggregated,
                 append only,        deduped,            query-optimized)
                 all history)        typed)
```

### Storage Layout Best Practices

```
# S3/GCS/ADLS path structure
s3://my-data-lake/
├── bronze/
│   └── ecommerce/
│       └── orders/
│           ├── year=2024/month=01/day=15/
│           │   └── part-00000.parquet
│           └── year=2024/month=01/day=16/
│               └── part-00000.parquet
├── silver/
│   └── ecommerce/
│       └── orders/
│           └── _delta_log/          ← Delta Lake transaction log
│           └── part-00000.parquet
└── gold/
    └── revenue_daily/
        └── part-00000.parquet

Partition by: (year, month) or (year, month, day) for daily jobs
Avoid partitioning by: high-cardinality columns (user_id, order_id)
File size target: 128MB–1GB per file
```

---

## Section 2 — Delta Lake (ACID on Data Lakes)

Delta Lake adds database-like guarantees to Parquet files on object storage.

```python
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from delta.tables import DeltaTable

builder = SparkSession.builder \
    .appName("DeltaLake ETL") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

spark = configure_spark_with_delta_pip(builder).getOrCreate()
```

### Writing Delta Tables

```python
# Initial write
orders_df.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("year", "month") \
    .save("s3://lake/silver/orders/")

# Append new data
new_orders.write \
    .format("delta") \
    .mode("append") \
    .save("s3://lake/silver/orders/")

# MERGE (upsert) — the killer feature of Delta Lake
delta_table = DeltaTable.forPath(spark, "s3://lake/silver/orders/")

delta_table.alias("target").merge(
    new_data.alias("source"),
    "target.id = source.id"
).whenMatchedUpdate(set={
    "status": "source.status",
    "total": "source.total",
    "updated_at": "source.updated_at",
}).whenNotMatchedInsert(values={
    "id": "source.id",
    "customer_id": "source.customer_id",
    "status": "source.status",
    "total": "source.total",
    "created_at": "source.created_at",
    "updated_at": "source.updated_at",
}).execute()
```

### Time Travel

```python
# Query historical version
spark.read \
    .format("delta") \
    .option("versionAsOf", 5) \           # specific version
    .load("s3://lake/silver/orders/")

spark.read \
    .format("delta") \
    .option("timestampAsOf", "2024-01-15 10:00:00") \  # point-in-time
    .load("s3://lake/silver/orders/")

# View history
delta_table = DeltaTable.forPath(spark, "s3://lake/silver/orders/")
delta_table.history(10).show()

# Restore to previous version
delta_table.restoreToVersion(3)

# Vacuum (clean up old files, default 7-day retention)
delta_table.vacuum(retentionHours=168)
```

### Schema Evolution

```python
# Merge schema changes automatically
new_data_with_new_col.write \
    .format("delta") \
    .option("mergeSchema", "true") \  # adds new columns
    .mode("append") \
    .save("s3://lake/silver/orders/")

# Overwrite schema completely
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")
```

---

## Section 3 — Change Data Capture (CDC) with Debezium

CDC captures every change (INSERT, UPDATE, DELETE) from a database in real time.

```
PostgreSQL WAL (Write-Ahead Log)
         ↓
    Debezium Connector
         ↓
    Kafka Topic (one per table)
         ↓
    Stream Processor (Spark/Flink)
         ↓
    Data Lake / DW
```

### Debezium PostgreSQL Connector Config

```json
{
  "name": "postgres-ecommerce-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "dbz_password",
    "database.dbname": "ecommerce",
    "database.server.name": "ecommerce",
    "table.include.list": "public.orders,public.customers,public.products",
    "publication.autocreate.mode": "filtered",
    "plugin.name": "pgoutput",
    "decimal.handling.mode": "double",
    "time.precision.mode": "adaptive",
    "tombstones.on.delete": "true",
    "topic.prefix": "cdc"
  }
}
```

### Processing CDC Events

```python
# CDC messages have this structure:
# {
#   "before": {old row or null for INSERT},
#   "after":  {new row or null for DELETE},
#   "op":     "c"=create, "u"=update, "d"=delete, "r"=read(snapshot)
# }

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StringType

cdc_schema = StructType() \
    .add("before", StructType()...) \
    .add("after", StructType()...) \
    .add("op", StringType()) \
    .add("ts_ms", "long")

cdc_stream = spark.readStream.format("kafka") \
    .option("subscribe", "cdc.public.orders") \
    .load() \
    .select(F.from_json(F.col("value").cast("string"), cdc_schema).alias("cdc")) \
    .select("cdc.*")

# Apply CDC to Delta Lake target
def apply_cdc(batch_df, batch_id):
    target = DeltaTable.forPath(spark, "s3://lake/silver/orders/")

    # Separate inserts/updates from deletes
    upserts = batch_df.filter(F.col("op").isin("c", "u", "r")).select("after.*")
    deletes = batch_df.filter(F.col("op") == "d").select("before.id")

    # Apply upserts
    if upserts.count() > 0:
        target.alias("t").merge(
            upserts.alias("s"), "t.id = s.id"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()

    # Apply deletes (soft delete)
    if deletes.count() > 0:
        target.update(
            condition=F.col("id").isin(deletes.select("id").rdd.flatMap(lambda x: x).collect()),
            set={"is_deleted": "true", "deleted_at": F.current_timestamp()}
        )

cdc_stream.writeStream.foreachBatch(apply_cdc) \
    .option("checkpointLocation", "/checkpoints/cdc_orders") \
    .start()
```

---

## Section 4 — Data Quality at Scale

```python
# Using Great Expectations for data quality
# pip install great_expectations

import great_expectations as ge

# Validate a Pandas/Spark DataFrame
df = spark.read.parquet("s3://lake/silver/orders/").toPandas()
ge_df = ge.from_pandas(df)

results = ge_df.expect_column_values_to_not_be_null("id")
results = ge_df.expect_column_values_to_be_unique("id")
results = ge_df.expect_column_values_to_be_between("total", min_value=0, max_value=1_000_000)
results = ge_df.expect_column_values_to_be_in_set("status", ["pending", "completed", "cancelled"])
results = ge_df.expect_column_pair_values_to_be_equal("updated_at", ">=", "created_at")

# Checkpoint: fail pipeline if expectations not met
validation_result = ge_df.validate()
if not validation_result["success"]:
    failed = [r for r in validation_result["results"] if not r["success"]]
    raise DataQualityError(f"Data quality checks failed: {failed}")
```

### Schema Enforcement

```python
# Enforce schema strictly in Spark
from pyspark.sql.utils import AnalysisException

EXPECTED_SCHEMA = StructType([
    StructField("id", IntegerType(), nullable=False),
    StructField("customer_id", IntegerType(), nullable=False),
    StructField("total", DoubleType(), nullable=False),
    StructField("status", StringType(), nullable=False),
])

def enforce_schema(df, expected):
    actual_fields = {f.name: f.dataType for f in df.schema.fields}
    expected_fields = {f.name: f.dataType for f in expected.fields}

    missing = set(expected_fields) - set(actual_fields)
    extra = set(actual_fields) - set(expected_fields)
    type_mismatches = {
        col: (actual_fields[col], expected_fields[col])
        for col in expected_fields
        if col in actual_fields and actual_fields[col] != expected_fields[col]
    }

    if missing or type_mismatches:
        raise SchemaError(f"Schema mismatch — missing: {missing}, type issues: {type_mismatches}")

    if extra:
        logger.warning(f"Extra columns (will be dropped): {extra}")

    return df.select([f.name for f in expected.fields])
```

---

## Section 5 — Horizontal Sharding (Database Level)

```sql
-- Application-level sharding: route writes based on a shard key

-- Shard 0: customers where id % 4 = 0
-- Shard 1: customers where id % 4 = 1
-- ...

-- In Python:
def get_shard(customer_id: int) -> str:
    shard_num = customer_id % 4
    return f"shard_{shard_num}"

# PostgreSQL partitioning is simpler for single-node sharding:
CREATE TABLE orders (
    id BIGINT,
    customer_id INTEGER
) PARTITION BY HASH (customer_id);

CREATE TABLE orders_p0 PARTITION OF orders FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE orders_p1 PARTITION OF orders FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE orders_p2 PARTITION OF orders FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE orders_p3 PARTITION OF orders FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

---

## 🏋️ Exercises

### Exercise 1 — Bronze → Silver Pipeline
Build a pipeline that:
- Reads raw CSV files from a "bronze" folder
- Validates schema, deduplicates, type-casts
- Writes to Delta Lake in "silver" folder
- Uses time travel to verify before/after a bad batch

### Exercise 2 — CDC Pipeline
Set up Debezium + Kafka (via Docker Compose).
Capture changes from PostgreSQL orders table.
Write a Spark Streaming job to sync changes to a Delta Lake table.

### Exercise 3 — Data Quality Gate
Add Great Expectations checks to your Airflow DAG.
Fail the pipeline if data quality checks don't pass.
Write checks for: not_null, unique, range, referential integrity.

---

## ✅ Self-Check Questions

1. What are the Bronze/Silver/Gold layers of a data lake?
2. What is Delta Lake and what ACID guarantees does it provide?
3. What is a MERGE operation in Delta Lake?
4. What is CDC and what does Debezium capture?
5. What is WAL (Write-Ahead Log)?
6. How does time travel work in Delta Lake?
7. What is partition pruning in a data lake?
8. What is schema evolution and why is it tricky?
9. What is a data quality checkpoint?
10. When would you use hash partitioning vs range partitioning?

---

## 🔗 Key Links

- https://docs.delta.io/latest/index.html
- https://debezium.io/documentation/reference/stable/
- https://greatexpectations.io/
- https://www.databricks.com/blog/2019/08/14/productionizing-machine-learning-with-delta-lake.html
