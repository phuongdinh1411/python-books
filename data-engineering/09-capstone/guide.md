# Pillar 9 — Capstone: End-to-End Data Platform

> **Duration:** 2 weeks | Combines ALL 8 pillars

---

## 🎯 Project Goal

Build an **end-to-end e-commerce analytics platform** that ingests, processes, stores,
and serves data using the full modern data engineering stack.

---

## 🏗️ Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                                    │
│  PostgreSQL (orders DB) · REST API (product catalog) · CSV (lookups) │
└────────────┬────────────────────────────────┬────────────────────────┘
             │                                │
     ┌───────▼──────┐                 ┌───────▼──────┐
     │  STREAMING    │                 │   BATCH       │
     │  Debezium     │                 │   Airflow     │
     │  → Kafka      │                 │   DAG (daily) │
     └───────┬───────┘                 └───────┬───────┘
             │                                 │
             └──────────────┬──────────────────┘
                            │
                 ┌──────────▼──────────┐
                 │   BRONZE LAYER       │
                 │   Raw Parquet / S3   │
                 │   (append only)      │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │   SILVER LAYER       │
                 │   Delta Lake         │
                 │   (clean, typed,     │
                 │    deduplicated)     │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │   GOLD LAYER / dbt   │
                 │   Star schema        │
                 │   Aggregates         │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │   SERVING            │
                 │   PostgreSQL DW      │
                 │   DuckDB (local SQL) │
                 └──────────────────────┘
```

---

## 📂 Project Structure

```
data-platform/
├── docker-compose.yml           # PostgreSQL, Kafka, Zookeeper, Airflow, Spark
├── pyproject.toml
├── README.md
│
├── infrastructure/
│   ├── kafka/
│   │   └── connectors/
│   │       └── postgres-cdc.json  # Debezium connector config
│   └── postgres/
│       └── init.sql               # Source DB schema + seed data
│
├── dags/                          # Airflow DAGs (Pillar 5)
│   ├── bronze_ingestion.py        # API → Bronze Parquet
│   ├── silver_processing.py       # Bronze → Silver Delta Lake
│   └── gold_dbt_run.py            # dbt models (Gold layer)
│
├── spark_jobs/                    # PySpark batch jobs (Pillar 6)
│   ├── bronze_to_silver.py
│   └── silver_to_gold.py
│
├── streaming/                     # Kafka consumers (Pillar 7)
│   ├── cdc_consumer.py            # CDC events → Bronze
│   └── metrics_consumer.py        # Real-time metrics
│
├── dbt/                           # dbt transformations (Pillar 5)
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_orders.sql
│   │   │   ├── stg_customers.sql
│   │   │   └── stg_products.sql
│   │   ├── intermediate/
│   │   │   └── int_orders_enriched.sql
│   │   └── marts/
│   │       ├── fct_orders.sql     # incremental
│   │       ├── dim_customers.sql  # SCD Type 2
│   │       ├── dim_products.sql
│   │       └── agg_revenue_daily.sql
│   └── tests/
│
├── extractors/                    # Data extractors (Pillar 5)
│   ├── api_extractor.py
│   └── db_extractor.py
│
├── quality/                       # Data quality (Pillar 8)
│   └── expectations/
│       ├── orders_suite.json
│       └── customers_suite.json
│
└── tests/
    ├── unit/
    │   ├── test_transformations.py
    │   └── test_quality_checks.py
    └── integration/
        └── test_pipeline_e2e.py
```

---

## Step-by-Step Build Guide

---

### Step 1 — Infrastructure (Day 1)

```yaml
# docker-compose.yml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports: ["5432:5432"]
    volumes:
      - ./infrastructure/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres
        -c wal_level=logical
        -c max_replication_slots=4
        -c max_wal_senders=4

  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.6.0
    depends_on: [zookeeper]
    ports: ["9092:9092"]
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"

  kafka-connect:
    image: confluentinc/cp-kafka-connect:7.6.0
    depends_on: [kafka, postgres]
    ports: ["8083:8083"]
    environment:
      CONNECT_BOOTSTRAP_SERVERS: kafka:9092
      CONNECT_REST_PORT: 8083
      CONNECT_GROUP_ID: "kafka-connect"
      CONNECT_CONFIG_STORAGE_TOPIC: "__connect_configs"
      CONNECT_OFFSET_STORAGE_TOPIC: "__connect_offsets"
      CONNECT_STATUS_STORAGE_TOPIC: "__connect_status"
      CONNECT_KEY_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_VALUE_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_PLUGIN_PATH: /usr/share/java,/usr/share/confluent-hub-components

  airflow:
    image: apache/airflow:2.9.0
    depends_on: [postgres]
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://postgres:password@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
    ports: ["8080:8080"]
```

---

### Step 2 — Source Database Schema (Day 1)

```sql
-- infrastructure/postgres/init.sql

-- Source OLTP schema
CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    full_name   VARCHAR(255),
    country     VARCHAR(100),
    segment     VARCHAR(50) DEFAULT 'regular',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    category    VARCHAR(100),
    price       NUMERIC(10,2),
    cost        NUMERIC(10,2),
    stock       INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    status      VARCHAR(50) DEFAULT 'pending',
    total       NUMERIC(10,2),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER REFERENCES orders(id),
    product_id  INTEGER REFERENCES products(id),
    quantity    INTEGER,
    unit_price  NUMERIC(10,2)
);

-- Enable logical replication for Debezium
CREATE PUBLICATION ecommerce_pub FOR TABLE customers, products, orders, order_items;

-- Seed data (run separately or via script)
INSERT INTO customers (email, full_name, country, segment)
SELECT
    'user' || gs || '@example.com',
    'User ' || gs,
    (ARRAY['US','UK','DE','FR','JP','SG'])[1 + (gs % 6)],
    (ARRAY['regular','premium','vip'])[1 + (gs % 3)]
FROM generate_series(1, 10000) AS gs;

INSERT INTO products (name, category, price, cost, stock)
SELECT
    'Product ' || gs,
    (ARRAY['Electronics','Clothing','Food','Books','Toys'])[1 + (gs % 5)],
    (gs % 500) + 10,
    ((gs % 500) + 10) * 0.6,
    (gs % 1000) + 50
FROM generate_series(1, 500) AS gs;

INSERT INTO orders (customer_id, status, total, created_at)
SELECT
    (gs % 10000) + 1,
    (ARRAY['pending','completed','cancelled'])[1 + (gs % 3)],
    (gs % 1000) + 50,
    NOW() - (gs % 365 || ' days')::INTERVAL
FROM generate_series(1, 100000) AS gs;
```

---

### Step 3 — Bronze Ingestion DAG (Day 2–3) — Pillar 5

```python
# dags/bronze_ingestion.py
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

BRONZE_PATH = Path("/data/lake/bronze")

@dag(
    dag_id="bronze_ingestion_daily",
    schedule="0 1 * * *",   # 1 AM UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["bronze", "daily"],
)
def bronze_ingestion():

    @task()
    def extract_orders(logical_date=None, **context) -> str:
        """Incremental extract from PostgreSQL."""
        start = context["data_interval_start"].isoformat()
        end   = context["data_interval_end"].isoformat()

        hook = PostgresHook(postgres_conn_id="source_postgres")
        df = hook.get_pandas_df("""
            SELECT o.*, c.country, c.segment
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.updated_at >= %(start)s AND o.updated_at < %(end)s
        """, parameters={"start": start, "end": end})

        if df.empty:
            print(f"No orders for {start} → {end}")
            return ""

        # Write to Bronze as Parquet
        date_str = logical_date.strftime("%Y/%m/%d")
        output_path = BRONZE_PATH / f"orders/{date_str}"
        output_path.mkdir(parents=True, exist_ok=True)

        table = pa.Table.from_pandas(df)
        pq.write_table(table, output_path / "orders.parquet", compression="snappy")

        print(f"Written {len(df)} rows to bronze/orders/{date_str}")
        return str(output_path)

    @task()
    def validate_bronze(parquet_path: str) -> dict:
        """Basic data quality check on bronze data."""
        if not parquet_path:
            return {"rows": 0, "valid": True}

        df = pd.read_parquet(parquet_path)
        issues = []

        null_ids = df["id"].isnull().sum()
        if null_ids > 0:
            issues.append(f"{null_ids} null ids")

        negative_totals = (df["total"] < 0).sum()
        if negative_totals > 0:
            issues.append(f"{negative_totals} negative totals")

        if issues:
            raise ValueError(f"Bronze validation failed: {issues}")

        return {"rows": len(df), "valid": True, "path": parquet_path}

    path = extract_orders()
    validate_bronze(path)

bronze_dag = bronze_ingestion()
```

---

### Step 4 — Silver Processing Spark Job (Day 3–4) — Pillar 6 + 8

```python
# spark_jobs/bronze_to_silver.py
from pyspark.sql import SparkSession, functions as F
from delta.tables import DeltaTable
from delta import configure_spark_with_delta_pip
import sys

def create_spark():
    builder = SparkSession.builder \
        .appName("Bronze to Silver") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.sql.shuffle.partitions", "50")
    return configure_spark_with_delta_pip(builder).getOrCreate()

def process_orders(spark, bronze_path: str, silver_path: str, date: str):
    # Read bronze
    bronze = spark.read.parquet(f"{bronze_path}/orders/year={date[:4]}/month={date[5:7]}/")

    # Clean and validate
    silver = bronze \
        .filter(F.col("id").isNotNull()) \
        .filter(F.col("total") >= 0) \
        .withColumn("status", F.lower(F.trim(F.col("status")))) \
        .withColumn("status",
            F.when(F.col("status").isin("pending", "completed", "cancelled"), F.col("status"))
             .otherwise(F.lit("unknown"))
        ) \
        .withColumn("total", F.col("total").cast("double")) \
        .withColumn("created_at", F.col("created_at").cast("timestamp")) \
        .withColumn("silver_processed_at", F.current_timestamp()) \
        .dropDuplicates(["id"])

    # Merge into Silver Delta Lake (idempotent)
    if DeltaTable.isDeltaTable(spark, silver_path):
        delta = DeltaTable.forPath(spark, silver_path)
        delta.alias("t").merge(
            silver.alias("s"), "t.id = s.id"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()
        print(f"Merged {silver.count()} rows into silver")
    else:
        silver.write.format("delta").save(silver_path)
        print(f"Created silver table with {silver.count()} rows")

if __name__ == "__main__":
    date = sys.argv[1]  # e.g. "2024-01-15"
    spark = create_spark()
    process_orders(
        spark,
        bronze_path="/data/lake/bronze",
        silver_path="/data/lake/silver/orders",
        date=date,
    )
```

---

### Step 5 — dbt Gold Layer (Day 5–6) — Pillar 5

```sql
-- dbt/models/staging/stg_orders.sql
WITH source AS (
    SELECT * FROM {{ source('silver', 'orders') }}
),
cleaned AS (
    SELECT
        id::INTEGER          AS order_id,
        customer_id::INTEGER AS customer_id,
        status,
        total::NUMERIC(10,2) AS total_amount,
        country,
        segment              AS customer_segment,
        created_at,
        updated_at
    FROM source
    WHERE id IS NOT NULL
      AND total >= 0
)
SELECT * FROM cleaned
```

```sql
-- dbt/models/marts/fct_orders.sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
    )
}}
WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
        WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),
date_dim AS (
    SELECT * FROM {{ ref('dim_date') }}
),
enriched AS (
    SELECT
        o.order_id,
        o.customer_id,
        d.date_key,
        d.year,
        d.month,
        d.quarter,
        d.is_weekend,
        o.status,
        o.total_amount,
        o.customer_segment,
        o.country,
        CASE
            WHEN o.total_amount >= 1000 THEN 'high'
            WHEN o.total_amount >= 100  THEN 'medium'
            ELSE 'low'
        END AS order_tier,
        o.created_at,
        o.updated_at
    FROM orders o
    LEFT JOIN date_dim d ON d.date_actual = o.created_at::DATE
)
SELECT * FROM enriched
```

```sql
-- dbt/models/marts/agg_revenue_daily.sql
{{
    config(materialized='table')
}}
SELECT
    created_at::DATE              AS date,
    country,
    customer_segment,
    COUNT(*)                      AS order_count,
    SUM(total_amount)             AS revenue,
    AVG(total_amount)             AS avg_order_value,
    COUNT(DISTINCT customer_id)   AS unique_customers,
    SUM(SUM(total_amount)) OVER (
        PARTITION BY country
        ORDER BY created_at::DATE
    )                             AS running_revenue_by_country
FROM {{ ref('fct_orders') }}
WHERE status = 'completed'
GROUP BY 1, 2, 3
ORDER BY 1, 2
```

---

### Step 6 — Streaming CDC Consumer (Day 7–8) — Pillar 7

```python
# streaming/cdc_consumer.py
"""
Consumes CDC events from Debezium → Kafka and writes to Bronze Parquet.
Runs continuously as a sidecar process.
"""
import json
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
from confluent_kafka import Consumer

logger = logging.getLogger(__name__)

TOPICS = ["cdc.public.orders", "cdc.public.customers", "cdc.public.products"]
BRONZE_PATH = Path("/data/lake/bronze/cdc")


def process_cdc_batch(records: list[dict]) -> None:
    """Write a batch of CDC records to Bronze."""
    for topic, group in _group_by_topic(records):
        table_name = topic.split(".")[-1]
        output_dir = BRONZE_PATH / table_name / datetime.utcnow().strftime("%Y/%m/%d")
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame([
            {
                "op": r["payload"]["op"],
                "ts_ms": r["payload"]["ts_ms"],
                **r["payload"]["after"],  # the new row state
            }
            for r in group
            if r["payload"]["after"]  # skip DELETEs for Bronze
        ])

        if not df.empty:
            timestamp = datetime.utcnow().strftime("%H%M%S%f")
            df.to_parquet(output_dir / f"part-{timestamp}.parquet", index=False)
            logger.info(f"Wrote {len(df)} CDC records for {table_name}")


def _group_by_topic(records):
    from itertools import groupby
    for key, group in groupby(records, lambda r: r["_topic"]):
        yield key, list(group)


def main():
    consumer = Consumer({
        "bootstrap.servers": "localhost:9092",
        "group.id": "cdc-bronze-writer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe(TOPICS)

    batch = []
    try:
        while True:
            msgs = consumer.consume(num_messages=500, timeout=2.0)
            for msg in msgs:
                if msg.error():
                    continue
                record = json.loads(msg.value())
                record["_topic"] = msg.topic()
                batch.append(record)

            if len(batch) >= 500:
                process_cdc_batch(batch)
                consumer.commit(asynchronous=False)
                batch = []
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
```

---

### Step 7 — Analytics Queries (Day 9) — Pillar 1–3

```sql
-- Query 1: Monthly revenue trend with MoM growth
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', date) AS month,
        SUM(revenue) AS revenue
    FROM agg_revenue_daily
    GROUP BY 1
)
SELECT
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month) AS prev_month,
    ROUND((revenue / LAG(revenue) OVER (ORDER BY month) - 1) * 100, 2) AS mom_growth_pct
FROM monthly
ORDER BY month;

-- Query 2: Customer cohort retention
WITH cohorts AS (
    SELECT customer_id, DATE_TRUNC('month', MIN(created_at)) AS cohort_month
    FROM fct_orders WHERE status = 'completed'
    GROUP BY 1
)
SELECT
    c.cohort_month,
    DATE_TRUNC('month', o.created_at) AS order_month,
    EXTRACT(MONTH FROM AGE(
        DATE_TRUNC('month', o.created_at), c.cohort_month
    ))::INTEGER AS months_since_first,
    COUNT(DISTINCT o.customer_id) AS active_customers
FROM fct_orders o
JOIN cohorts c ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
GROUP BY 1, 2, 3
ORDER BY 1, 3;

-- Query 3: Top products by revenue with rankings
SELECT
    p.name AS product,
    p.category,
    SUM(oi.quantity * oi.unit_price) AS revenue,
    SUM(oi.quantity) AS units_sold,
    RANK() OVER (PARTITION BY p.category ORDER BY SUM(oi.quantity * oi.unit_price) DESC) AS rank_in_category,
    ROUND(SUM(oi.quantity * oi.unit_price) /
          SUM(SUM(oi.quantity * oi.unit_price)) OVER () * 100, 2) AS revenue_pct
FROM fct_orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN dim_products p ON oi.product_id = p.product_id
WHERE o.status = 'completed'
  AND o.created_at >= NOW() - INTERVAL '90 days'
GROUP BY 1, 2
ORDER BY revenue DESC
LIMIT 50;
```

---

### Step 8 — DuckDB Analytics Layer (Day 10) — Pillar 4

```python
# analytics/query_engine.py
import duckdb
from pathlib import Path

class AnalyticsEngine:
    """Fast local analytics over Parquet using DuckDB."""

    def __init__(self, lake_path: str):
        self.con = duckdb.connect()
        self.lake = Path(lake_path)

        # Register virtual tables pointing to Parquet files
        self.con.execute(f"""
            CREATE VIEW orders AS
            SELECT * FROM read_parquet('{self.lake}/silver/orders/**/*.parquet');

            CREATE VIEW customers AS
            SELECT * FROM read_parquet('{self.lake}/silver/customers/**/*.parquet');

            CREATE VIEW products AS
            SELECT * FROM read_parquet('{self.lake}/silver/products/**/*.parquet');
        """)

    def revenue_by_country(self, days: int = 30):
        return self.con.execute(f"""
            SELECT
                country,
                COUNT(*) AS orders,
                SUM(total_amount) AS revenue,
                AVG(total_amount) AS avg_order
            FROM orders
            WHERE status = 'completed'
              AND created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY country
            ORDER BY revenue DESC
        """).df()

    def customer_ltv_distribution(self):
        return self.con.execute("""
            SELECT
                NTILE(10) OVER (ORDER BY ltv) AS decile,
                MIN(ltv) AS min_ltv,
                MAX(ltv) AS max_ltv,
                AVG(ltv) AS avg_ltv,
                COUNT(*) AS customers
            FROM (
                SELECT customer_id, SUM(total_amount) AS ltv
                FROM orders WHERE status = 'completed'
                GROUP BY customer_id
            ) t
            GROUP BY 1
            ORDER BY 1
        """).df()
```

---

## ✅ Done Checklist

### Infrastructure
- [ ] Docker Compose: PostgreSQL, Kafka, Kafka Connect, Airflow
- [ ] Source DB seeded with 100K+ orders
- [ ] Debezium CDC connector registered and streaming changes

### Pipelines
- [ ] Bronze ingestion DAG (daily, incremental, retries)
- [ ] Silver Spark job (clean, dedup, Delta Lake merge)
- [ ] CDC consumer writing to Bronze
- [ ] dbt models: staging → intermediate → marts
- [ ] All dbt tests passing

### Queries & Analytics
- [ ] Revenue trend with MoM growth
- [ ] Customer cohort retention matrix
- [ ] Top products with ranking per category
- [ ] Funnel analysis
- [ ] DuckDB analytics engine for ad-hoc queries

### Quality & Observability
- [ ] Data quality checks in Bronze → Silver step
- [ ] Schema enforcement
- [ ] Pipeline run metrics table
- [ ] Consumer lag monitoring script

---

## 📊 Skills Demonstrated

| Skill | Where Used |
|-------|-----------|
| Advanced SQL | Analytics queries, cohort, funnel, window functions |
| PostgreSQL | Source DB, DW, partitioning, JSONB |
| Query Optimization | EXPLAIN ANALYZE on analytics queries |
| Analytical Stores | DuckDB for ad-hoc, Parquet throughout |
| ETL / ELT Pipelines | Airflow DAGs, dbt models |
| Batch Processing | PySpark Bronze → Silver job |
| Streaming | Debezium + Kafka CDC consumer |
| Large-Scale Processing | Delta Lake, Bronze/Silver/Gold, schema evolution |

---

## 🎓 Congratulations!

You have built a complete data platform covering the entire modern data engineering stack.
This project demonstrates everything the job requirement asks for.

**Next steps:**
1. Deploy on AWS (S3 + EMR + RDS + MSK)
2. Add observability: OpenLineage / DataHub for data lineage
3. Add reverse ETL: sync DW aggregates back to operational systems
4. Add ML feature store on top of the Silver layer
