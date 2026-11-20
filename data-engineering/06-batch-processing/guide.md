# Pillar 6 — Batch Processing (Spark & Polars)

> **Duration:** 2 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Understand Spark's distributed execution model (RDD, DataFrame, Catalyst)
- Write PySpark jobs for large-scale batch transformations
- Use Polars for fast single-machine processing (pandas replacement)
- Optimize Spark jobs: partitioning, caching, broadcast joins, avoid shuffles
- Read/write Parquet, Delta Lake, and databases in Spark

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [*Learning Spark 2nd Ed* (Free PDF — Databricks)](https://www.databricks.com/resources/ebook/learning-spark-lightning-fast-data-analytics) | 📖 Book | ✅ Free (registration required) |
| [PySpark Official Docs](https://spark.apache.org/docs/latest/api/python/) | 📄 Docs | ✅ Free |
| [Spark SQL & DataFrames Guide](https://spark.apache.org/docs/latest/sql-programming-guide.html) | 📄 Docs | ✅ Free |
| [Polars User Guide](https://docs.pola.rs/) | 📄 Docs | ✅ Free |
| [Data + AI Summit talks (YouTube — Databricks)](https://www.youtube.com/@Databricks) | 🎥 Videos | ✅ Free |
| [Spark Performance Tuning Guide](https://spark.apache.org/docs/latest/tuning.html) | 📄 Docs | ✅ Free |

---

## Section 1 — Spark Architecture

```
Driver Program
  │   Creates SparkContext, SparkSession
  │   Builds execution plan (DAG of transformations)
  │   Sends tasks to Cluster Manager
  │
  ├─→ Cluster Manager (YARN / Kubernetes / Spark Standalone)
  │       Allocates resources (Executors)
  │
  └─→ Executor 1 ──→ Task 1, Task 2, Task 3  (each task = one partition)
      Executor 2 ──→ Task 4, Task 5, Task 6
      Executor 3 ──→ Task 7, Task 8, Task 9

Partition  = one chunk of data (aim for 128MB–1GB per partition)
Stage      = set of tasks with no shuffle boundary
Shuffle    = redistribute data across executors (expensive!)
```

### Lazy Evaluation

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("ETL Job") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()

# TRANSFORMATIONS are lazy — no work done yet
df = spark.read.parquet("s3://bucket/orders/")            # 1. read
df2 = df.filter("status = 'completed'")                  # 2. filter
df3 = df2.groupBy("customer_id").agg({"total": "sum"})   # 3. aggregate

# ACTION triggers execution — all steps run now
df3.write.parquet("s3://bucket/output/")                  # trigger!
df3.show()                                                 # trigger!
df3.count()                                                # trigger!

# Check the execution plan BEFORE running
df3.explain(mode="formatted")  # shows physical plan, optimizations applied
```

---

## Section 2 — PySpark DataFrames

### Reading Data

```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, DoubleType, TimestampType

spark = SparkSession.builder.appName("ETL").getOrCreate()

# Explicit schema (always better than inferSchema for large files)
schema = StructType([
    StructField("id", IntegerType(), nullable=False),
    StructField("customer_id", IntegerType(), nullable=True),
    StructField("status", StringType(), nullable=True),
    StructField("total", DoubleType(), nullable=True),
    StructField("created_at", TimestampType(), nullable=True),
])

# CSV
df = spark.read.csv("orders.csv", schema=schema, header=True)

# Parquet (preferred — has schema embedded)
df = spark.read.parquet("s3://bucket/orders/year=2024/month=*/")

# JSON
df = spark.read.json("events.json")

# JDBC (database)
df = spark.read.jdbc(
    url="jdbc:postgresql://host:5432/mydb",
    table="orders",
    properties={"user": "user", "password": "pass", "driver": "org.postgresql.Driver"},
    numPartitions=10,              # read in parallel
    partitionColumn="id",
    lowerBound=1,
    upperBound=10_000_000,
)
```

### Transformations

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Filter and select
df = orders.filter(
    (F.col("status") == "completed") &
    (F.col("total") > 0) &
    (F.col("created_at") >= F.lit("2024-01-01").cast("timestamp"))
).select("id", "customer_id", "total", "created_at")

# Derived columns
df = orders.withColumn(
    "total_cents", (F.col("total") * 100).cast("integer")
).withColumn(
    "order_month", F.date_trunc("month", F.col("created_at"))
).withColumn(
    "is_high_value", F.when(F.col("total") >= 1000, True).otherwise(False)
).withColumn(
    "clean_status", F.lower(F.trim(F.col("status")))
).drop("raw_status")

# Rename
df = df.withColumnRenamed("customer_id", "cust_id")

# Type casting
df = df.withColumn("total", F.col("total").cast("double"))

# Null handling
df = df.fillna({"status": "unknown", "total": 0.0})
df = df.dropna(subset=["id", "customer_id"])

# String operations
df = df.withColumn(
    "email_domain",
    F.regexp_extract(F.col("email"), "@(.+)$", 1)
)
```

### Aggregations

```python
from pyspark.sql import functions as F

# Group by with multiple aggregations
result = orders.groupBy("customer_id", "status").agg(
    F.count("id").alias("order_count"),
    F.sum("total").alias("total_revenue"),
    F.avg("total").alias("avg_order"),
    F.min("created_at").alias("first_order"),
    F.max("created_at").alias("last_order"),
    F.approx_count_distinct("product_id").alias("unique_products"),
    F.percentile_approx("total", 0.5).alias("median_total"),
)

# Pivot
pivoted = orders.groupBy("customer_id").pivot("status").agg(F.sum("total"))
# Creates columns: customer_id | completed | pending | cancelled

# Window functions
window_spec = Window.partitionBy("customer_id").orderBy("created_at")

enriched = orders.withColumn(
    "row_num", F.row_number().over(window_spec)
).withColumn(
    "running_total", F.sum("total").over(window_spec)
).withColumn(
    "prev_order_total", F.lag("total", 1).over(window_spec)
).withColumn(
    "cumulative_rank", F.percent_rank().over(window_spec)
)
```

### Joins

```python
# Standard join
result = orders.join(
    customers,
    on="customer_id",
    how="left"   # inner, left, right, full, cross, semi, anti
)

# Join on multiple columns
result = fact_table.join(
    dim_table,
    on=(fact_table.product_id == dim_table.id) &
       (fact_table.valid_date.between(dim_table.start_date, dim_table.end_date)),
    how="left"
)

# BROADCAST JOIN — critical optimization for small dimension tables!
from pyspark.sql.functions import broadcast

# If customers is small (<= spark.sql.autoBroadcastJoinThreshold, default 10MB):
result = orders.join(
    broadcast(customers),   # explicitly broadcast
    on="customer_id",
    how="left"
)
# Avoids shuffle! Each executor gets full copy of customers in memory.
# Huge speedup when joining large table with small lookup table.
```

---

## Section 3 — Spark Optimization

### Partitioning Strategy

```python
# Check current partition count
print(df.rdd.getNumPartitions())

# Too few partitions → not enough parallelism
# Too many partitions → too much overhead

# Target: each partition = 128MB–1GB on disk
# Rule: (data_size_bytes / 128MB) partitions, minimum = num_executors * num_cores

# Repartition (triggers shuffle — use for joins)
df = df.repartition(200, "customer_id")  # partition by column for co-location

# Coalesce (no shuffle — use to reduce partition count after filtering)
df = df.coalesce(10)  # reduce from 200 to 10 partitions (no shuffle!)

# Set shuffle partitions (default 200, often needs tuning)
spark.conf.set("spark.sql.shuffle.partitions", "400")
```

### Caching

```python
from pyspark import StorageLevel

# Cache in memory (default)
df.cache()
# or:
df.persist(StorageLevel.MEMORY_ONLY)

# Cache to disk if doesn't fit in memory
df.persist(StorageLevel.MEMORY_AND_DISK)

# When to cache:
# ✅ DataFrame used multiple times in the same job
# ❌ DataFrame used only once (wastes memory, adds overhead)

customers.cache()  # used in 3 different joins below — cache it!
orders.join(broadcast(customers), ...)
returns.join(broadcast(customers), ...)
refunds.join(broadcast(customers), ...)

# Unpersist when done
customers.unpersist()
```

### Avoiding Common Performance Traps

```python
# 1. SKEW: some partitions are much larger than others
# Check with:
df.groupBy(F.spark_partition_id()).count().orderBy("count", ascending=False).show()

# Fix: salt the skewed key
from pyspark.sql import functions as F

SALT = 10
large_df = large_df.withColumn(
    "salted_key",
    F.concat(F.col("customer_id"), F.lit("_"), (F.rand() * SALT).cast("int"))
)
small_df_salted = small_df.withColumn(
    "salt_id", F.explode(F.array([F.lit(i) for i in range(SALT)]))
).withColumn("salted_key", F.concat(F.col("customer_id"), F.lit("_"), F.col("salt_id")))

result = large_df.join(small_df_salted, on="salted_key")

# 2. UDFs are slow (Python ↔ JVM serialization)
# BAD:
from pyspark.sql.types import StringType
@F.udf(returnType=StringType())
def clean_status(s):
    return s.lower().strip() if s else None

df.withColumn("status", clean_status("status"))  # slow!

# GOOD: use built-in Spark functions
df.withColumn("status", F.lower(F.trim(F.col("status"))))  # fast!

# If you MUST use UDF, use Pandas UDF (vectorized)
from pyspark.sql.functions import pandas_udf
import pandas as pd

@pandas_udf("string")
def clean_status_fast(series: pd.Series) -> pd.Series:
    return series.str.lower().str.strip()

df.withColumn("status", clean_status_fast("status"))  # 100x faster than regular UDF
```

---

## Section 4 — Polars (Fast Single-Machine Processing)

Polars is a Rust-based DataFrame library — faster than Pandas, easier than Spark.
Use it when data fits in memory (single machine, up to ~100GB RAM).

```python
import polars as pl

# Reading
df = pl.read_csv("orders.csv")
df = pl.read_parquet("orders.parquet")
df = pl.read_parquet("data/*.parquet")  # glob

# Lazy mode (like Spark — optimized execution)
df = pl.scan_parquet("data/*.parquet")  # lazy!
result = (
    df
    .filter(pl.col("status") == "completed")
    .filter(pl.col("total") > 0)
    .group_by("customer_id")
    .agg([
        pl.col("total").sum().alias("lifetime_value"),
        pl.col("id").count().alias("order_count"),
        pl.col("created_at").max().alias("last_order"),
    ])
    .sort("lifetime_value", descending=True)
).collect()  # trigger execution

# Expressions — composable, powerful
result = df.with_columns([
    pl.col("total").cast(pl.Float64),
    pl.col("created_at").str.to_datetime(),
    (pl.col("total") * 100).round(0).alias("total_cents"),
    pl.col("status").str.to_lowercase().str.strip_chars().alias("clean_status"),
    pl.when(pl.col("total") >= 1000)
      .then(pl.lit("high"))
      .when(pl.col("total") >= 100)
      .then(pl.lit("medium"))
      .otherwise(pl.lit("low"))
      .alias("tier"),
])

# Window functions
result = df.with_columns([
    pl.col("total").sum().over("customer_id").alias("customer_total"),
    pl.col("total").rank(descending=True).over("customer_id").alias("order_rank"),
    pl.col("total").shift(1).over("customer_id").alias("prev_order"),
    pl.col("total").rolling_mean(window_size=7).over("customer_id").alias("rolling_avg"),
])

# Joins
result = orders.join(
    customers.select(["id", "full_name", "country"]),
    left_on="customer_id",
    right_on="id",
    how="left",
)

# Aggregation
result = df.group_by(["country", pl.col("created_at").dt.month().alias("month")]).agg([
    pl.col("id").count().alias("orders"),
    pl.col("total").sum().alias("revenue"),
    pl.col("total").median().alias("median_order"),
    pl.col("total").quantile(0.95).alias("p95_order"),
])
```

### Polars vs Pandas Performance

```python
import polars as pl
import pandas as pd
import time

# Generate 10M rows
n = 10_000_000
data = {"id": range(n), "value": [i % 1000 for i in range(n)], "group": [f"g{i%100}" for i in range(n)]}

# Pandas
df_pd = pd.DataFrame(data)
t = time.perf_counter()
result_pd = df_pd.groupby("group")["value"].agg(["sum", "mean", "std"])
print(f"Pandas: {time.perf_counter() - t:.2f}s")

# Polars
df_pl = pl.DataFrame(data)
t = time.perf_counter()
result_pl = df_pl.group_by("group").agg([
    pl.col("value").sum(), pl.col("value").mean(), pl.col("value").std()
])
print(f"Polars: {time.perf_counter() - t:.2f}s")  # Usually 5-20x faster!
```

---

## 🏋️ Exercises

### Exercise 1 — PySpark ETL Job
Build a Spark job that:
- Reads 1M+ orders from Parquet
- Joins with customers and products
- Computes customer lifetime value and order statistics
- Writes output as partitioned Parquet by country and year

### Exercise 2 — Spark Optimization
Take a slow Spark job. Use `explain()` and Spark UI to:
- Identify shuffles
- Find skewed partitions
- Fix with broadcast join or salting
- Measure speedup

### Exercise 3 — Polars Pipeline
Rewrite a pandas data pipeline in Polars using lazy mode.
Benchmark and compare memory usage and execution time.

---

## ✅ Self-Check Questions

1. What is lazy evaluation in Spark?
2. What is a shuffle and why is it expensive?
3. When should you use a broadcast join?
4. What is partition skew and how do you detect it?
5. Why are regular Python UDFs slow in Spark?
6. What is the difference between `repartition` and `coalesce`?
7. When would you use Polars instead of Spark?
8. What does `explain(mode="formatted")` show?
9. What is a Pandas UDF?
10. What is the Catalyst optimizer?

---

## 🔗 Key Links

- https://spark.apache.org/docs/latest/api/python/
- https://docs.pola.rs/
- https://www.databricks.com/blog/2015/04/13/deep-dive-into-spark-sqls-catalyst-optimizer.html
