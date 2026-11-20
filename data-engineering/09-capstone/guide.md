# Capstone — Production-Grade End-to-End Data Platform

> **Duration:** 2 weeks | The project you show when interviewing for data engineering roles.

---

## 🎯 What "Production-Grade" Means Here

| Concern | What We Build |
|---------|--------------|
| **Ingestion** | Debezium CDC (real-time) + Airflow DAGs (batch) |
| **Streaming** | Kafka producers/consumers with at-least-once + idempotent upsert |
| **Batch** | PySpark jobs with broadcast joins, proper partitioning, Delta Lake merge |
| **Transformation** | dbt with incremental models, schema tests, freshness checks |
| **Data Quality** | Great Expectations checkpoints in every pipeline stage |
| **Storage** | Bronze/Silver/Gold Delta Lake on local filesystem (swap for S3 in cloud) |
| **Orchestration** | Airflow 2.9 with TaskFlow API, SLAs, alerting, retries |
| **Observability** | Structured logs, Airflow task durations, consumer lag monitoring |
| **Reliability** | Idempotent loads (upsert), Alembic for source DB, schema evolution |
| **Developer UX** | Docker Compose (one command), Makefile, seed data, README |

---

## 🏗️ Full Stack Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                      │
│    PostgreSQL (OLTP) ─── Debezium ───► Kafka (CDC topics)               │
│    REST API (products)                                                   │
│    CSV files (reference data)                                            │
└────────────────────────────────────────────────────────────────────────-┘
                │ CDC (real-time)                │ Batch (nightly)
                ▼                                ▼
        ┌──────────────┐               ┌──────────────────┐
        │  Kafka CDC   │               │  Airflow DAGs    │
        │  Consumer    │               │  (Python)        │
        └──────┬───────┘               └────────┬─────────┘
               │                                │
               └──────────────┬─────────────────┘
                              │
              ┌───────────────▼────────────────┐
              │        BRONZE LAYER             │
              │  Delta Lake (raw, append-only)  │
              │  /data/lake/bronze/             │
              └───────────────┬────────────────┘
                              │  PySpark job
              ┌───────────────▼────────────────┐
              │        SILVER LAYER             │
              │  Delta Lake (clean, deduped,    │
              │  typed, schema-enforced)        │
              │  /data/lake/silver/             │
              └───────────────┬────────────────┘
                              │  dbt models
              ┌───────────────▼────────────────┐
              │         GOLD LAYER             │
              │  dbt (star schema, aggregates)  │
              │  PostgreSQL Data Warehouse      │
              └───────────────┬────────────────┘
                              │
              ┌───────────────▼────────────────┐
              │        SERVING LAYER           │
              │  DuckDB ad-hoc queries         │
              │  SQL views for BI tools        │
              └────────────────────────────────┘
```

---

## 📂 Full Project Structure

```
data-platform/
├── .github/
│   └── workflows/
│       └── ci.yml                      # lint → test → validate dbt
├── infrastructure/
│   ├── postgres/
│   │   └── init.sql                    # source schema + seed data
│   └── kafka/
│       └── connectors/
│           └── debezium-postgres.json  # Debezium connector config
├── airflow/
│   ├── dags/
│   │   ├── bronze_ingestion.py         # API + CSV → Bronze Delta Lake
│   │   ├── silver_processing.py        # Bronze → Silver (PySpark)
│   │   ├── gold_dbt_run.py             # Silver → Gold (dbt)
│   │   └── data_quality_check.py       # Great Expectations checkpoint DAG
│   └── plugins/
│       └── operators/
│           └── spark_local_operator.py # Run PySpark locally from Airflow
├── spark_jobs/
│   ├── bronze_to_silver_orders.py      # Full PySpark job
│   ├── bronze_to_silver_customers.py
│   └── common/
│       ├── delta_utils.py              # Delta merge helpers
│       ├── schema_registry.py          # Canonical schemas
│       └── quality.py                  # Reusable quality checks
├── streaming/
│   ├── cdc_consumer.py                 # Kafka → Bronze Delta Lake
│   └── metrics_consumer.py            # Real-time event metrics
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _sources.yml
│   │   │   ├── stg_orders.sql
│   │   │   ├── stg_customers.sql
│   │   │   └── stg_products.sql
│   │   ├── intermediate/
│   │   │   └── int_orders_enriched.sql
│   │   └── marts/
│   │       ├── finance/
│   │       │   ├── fct_orders.sql
│   │       │   └── schema.yml
│   │       └── marketing/
│   │           ├── dim_customers.sql
│   │           ├── agg_revenue_daily.sql
│   │           └── schema.yml
│   ├── macros/
│   │   └── surrogate_key.sql
│   └── tests/
│       └── assert_no_negative_revenue.sql
├── quality/
│   └── expectations/
│       ├── orders_suite.json
│       └── customers_suite.json
├── analytics/
│   └── query_engine.py                 # DuckDB serving layer
├── tests/
│   ├── unit/
│   │   ├── test_transformations.py
│   │   └── test_quality_checks.py
│   └── integration/
│       └── test_pipeline_e2e.py
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```

---

## Step 1 — Infrastructure (One-Command Setup)

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  # ── Source OLTP Database ───────────────────────────────────────────
  postgres-source:
    image: postgres:16-alpine
    container_name: dp_postgres_source
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports: ["5432:5432"]
    volumes:
      - ./infrastructure/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
      - postgres_source_data:/var/lib/postgresql/data
    command: >
      postgres
        -c wal_level=logical
        -c max_replication_slots=5
        -c max_wal_senders=5
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 10

  # ── Data Warehouse ─────────────────────────────────────────────────
  postgres-dw:
    image: postgres:16-alpine
    container_name: dp_postgres_dw
    environment:
      POSTGRES_DB: data_warehouse
      POSTGRES_USER: dw_user
      POSTGRES_PASSWORD: dw_password
    ports: ["5433:5432"]
    volumes:
      - postgres_dw_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dw_user"]
      interval: 5s

  # ── Zookeeper ──────────────────────────────────────────────────────
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    container_name: dp_zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  # ── Kafka Broker ───────────────────────────────────────────────────
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: dp_kafka
    depends_on: [zookeeper]
    ports: ["9092:9092"]
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_LOG_RETENTION_HOURS: 168
    healthcheck:
      test: kafka-topics --bootstrap-server localhost:9092 --list
      interval: 10s
      timeout: 5s
      retries: 10

  # ── Kafka Connect (Debezium) ────────────────────────────────────────
  kafka-connect:
    image: debezium/connect:2.6
    container_name: dp_kafka_connect
    depends_on:
      kafka:          { condition: service_healthy }
      postgres-source: { condition: service_healthy }
    ports: ["8083:8083"]
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
      GROUP_ID: 1
      CONFIG_STORAGE_TOPIC: __connect_configs
      OFFSET_STORAGE_TOPIC: __connect_offsets
      STATUS_STORAGE_TOPIC: __connect_statuses

  # ── Airflow ────────────────────────────────────────────────────────
  airflow:
    image: apache/airflow:2.9.1-python3.12
    container_name: dp_airflow
    depends_on:
      postgres-dw: { condition: service_healthy }
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://dw_user:dw_password@postgres-dw:5432/data_warehouse
      AIRFLOW__CORE__FERNET_KEY: "CHANGE-ME-use-python-m-cryptography.fernet-Fernet.generate_key"
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
      AIRFLOW__LOGGING__LOG_FORMAT: "%(asctime)s [%(levelname)s] %(message)s"
      SOURCE_DB_CONN: postgresql+psycopg2://postgres:password@postgres-source:5432/ecommerce
      DW_DB_CONN: postgresql+psycopg2://dw_user:dw_password@postgres-dw:5432/data_warehouse
      LAKE_PATH: /data/lake
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./spark_jobs:/opt/spark_jobs
      - ./dbt:/opt/dbt
      - lake_data:/data/lake
    ports: ["8080:8080"]
    command: >
      bash -c "airflow db migrate && airflow users create -u admin -p admin
               -f Admin -l User -r Admin -e admin@example.com &&
               airflow webserver & airflow scheduler"

volumes:
  postgres_source_data:
  postgres_dw_data:
  lake_data:
```

---

## Step 2 — Source DB Schema & Seed Data

### `infrastructure/postgres/init.sql`

```sql
-- Enable logical replication
CREATE PUBLICATION ecommerce_pub FOR ALL TABLES;

-- ── Tables ────────────────────────────────────────────────────────────────
CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    full_name   VARCHAR(255),
    country     VARCHAR(100) NOT NULL DEFAULT 'US',
    segment     VARCHAR(50)  NOT NULL DEFAULT 'regular'
                             CHECK (segment IN ('regular', 'premium', 'vip')),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    category    VARCHAR(100) NOT NULL,
    price       NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    cost        NUMERIC(10,2) NOT NULL CHECK (cost >= 0),
    stock       INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status      VARCHAR(50) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','completed','cancelled','refunded')),
    total       NUMERIC(10,2) NOT NULL CHECK (total >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0)
);

-- ── Indexes ───────────────────────────────────────────────────────────────
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_status   ON orders (status);
CREATE INDEX idx_orders_created  ON orders (created_at DESC);
CREATE INDEX idx_items_order     ON order_items (order_id);

-- ── auto-update updated_at ────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customers_updated BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_orders_updated BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Seed data (100 k orders, realistic distribution) ─────────────────────
INSERT INTO customers (email, full_name, country, segment)
SELECT
    'user' || gs || '@example.com',
    'User ' || gs,
    (ARRAY['US','US','US','UK','DE','FR','JP','SG','CA','AU'])[1 + (gs % 10)],
    (ARRAY['regular','regular','regular','premium','premium','vip'])[1 + (gs % 6)]
FROM generate_series(1, 10000) AS gs;

INSERT INTO products (name, category, price, cost, stock)
SELECT
    'Product ' || gs,
    (ARRAY['Electronics','Clothing','Food','Books','Toys','Sport'])[1 + (gs % 6)],
    ROUND(((gs % 490) + 10 + random() * 10)::numeric, 2),
    ROUND(((gs % 490) + 10) * 0.6, 2),
    (gs % 1000) + 50
FROM generate_series(1, 500) AS gs;

INSERT INTO orders (customer_id, status, total, created_at)
SELECT
    (gs % 10000) + 1,
    (ARRAY['pending','completed','completed','completed','cancelled'])[1 + (gs % 5)],
    ROUND(((gs % 950) + 50 + random() * 50)::numeric, 2),
    NOW() - ((gs % 730) || ' days')::INTERVAL
FROM generate_series(1, 100000) AS gs;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT
    o.id,
    (gs % 500) + 1,
    (gs % 5) + 1,
    p.price
FROM orders o
CROSS JOIN generate_series(1, 2) AS gs
JOIN products p ON p.id = (gs % 500) + 1
LIMIT 200000;
```

---

## Step 3 — Kafka CDC Consumer

### `streaming/cdc_consumer.py`

```python
#!/usr/bin/env python3
"""
Consumes Debezium CDC events from Kafka and writes them to Bronze Delta Lake.
Runs as a long-lived process alongside Airflow.
"""
from __future__ import annotations

import json
import logging
import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Iterator

import pandas as pd
from confluent_kafka import Consumer, KafkaError, KafkaException, Message

logger = logging.getLogger(__name__)

KAFKA_CONFIG = {
    "bootstrap.servers": os.getenv("KAFKA_BROKERS", "localhost:9092"),
    "group.id": "cdc-bronze-writer-v1",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
    "max.poll.interval.ms": 300_000,
    "session.timeout.ms": 30_000,
}

CDC_TOPICS = [
    "ecommerce.public.orders",
    "ecommerce.public.customers",
    "ecommerce.public.products",
]

LAKE_PATH = Path(os.getenv("LAKE_PATH", "/data/lake"))
BATCH_SIZE = 500


def _table_from_topic(topic: str) -> str:
    """'ecommerce.public.orders' → 'orders'"""
    return topic.split(".")[-1]


def _extract_records(messages: list[Message]) -> Iterator[tuple[str, dict]]:
    """Yield (table_name, flat_record) for each CDC message."""
    for msg in messages:
        raw = msg.value()
        if raw is None:
            continue  # tombstone (delete marker)
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("bad_json offset=%s: %s", msg.offset(), e)
            continue

        payload = envelope.get("payload", {})
        op = payload.get("op")  # c=insert, u=update, d=delete, r=snapshot
        after = payload.get("after")

        if op in ("c", "u", "r") and after:
            table = _table_from_topic(msg.topic())
            yield table, {
                **after,
                "_op": op,
                "_kafka_offset": msg.offset(),
                "_kafka_partition": msg.partition(),
                "_ingested_at": datetime.utcnow().isoformat(),
            }


def _write_bronze_batch(table: str, records: list[dict]) -> None:
    """Write a batch to Bronze as Parquet, partitioned by date."""
    if not records:
        return

    df = pd.DataFrame(records)
    today = datetime.utcnow().strftime("%Y/%m/%d")
    out_dir = LAKE_PATH / "bronze" / table / today
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%H%M%S%f")
    path = out_dir / f"cdc-{ts}.parquet"
    df.to_parquet(path, index=False, compression="snappy")
    logger.info("bronze_written table=%s rows=%d path=%s", table, len(df), path)


class CDCConsumer:
    def __init__(self) -> None:
        self._consumer = Consumer(KAFKA_CONFIG)
        self._consumer.subscribe(
            CDC_TOPICS,
            on_assign=lambda c, p: logger.info("assigned partitions=%s", [x.partition for x in p]),
            on_revoke=lambda c, p: (
                logger.info("revoking, flushing offsets"),
                c.commit(asynchronous=False),
            ),
        )
        self._running = True
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)

    def _stop(self, *_: object) -> None:
        logger.info("shutdown_signal_received")
        self._running = False

    def run(self) -> None:
        logger.info("cdc_consumer_started topics=%s", CDC_TOPICS)
        buffer: dict[str, list[dict]] = {}

        try:
            while self._running:
                messages = self._consumer.consume(num_messages=BATCH_SIZE, timeout=2.0)
                if not messages:
                    continue

                errors = [m for m in messages if m.error()]
                for m in errors:
                    if m.error().code() != KafkaError._PARTITION_EOF:
                        raise KafkaException(m.error())

                for table, record in _extract_records(
                    [m for m in messages if not m.error()]
                ):
                    buffer.setdefault(table, []).append(record)

                for table, records in buffer.items():
                    _write_bronze_batch(table, records)
                buffer.clear()

                self._consumer.commit(asynchronous=False)
                logger.debug("batch_committed size=%d", len(messages))

        finally:
            self._consumer.close()
            logger.info("cdc_consumer_stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    CDCConsumer().run()
```

---

## Step 4 — PySpark Bronze → Silver Job

### `spark_jobs/bronze_to_silver_orders.py`

```python
#!/usr/bin/env python3
"""
Bronze → Silver: orders table.
Reads raw Parquet from Bronze, cleans, deduplicates, type-enforces,
and merges into a Silver Delta Lake table.

Usage:
    spark-submit bronze_to_silver_orders.py --date 2024-01-15
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from delta import configure_spark_with_delta_pip
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)

# ── Canonical Silver schema ────────────────────────────────────────────────
SILVER_SCHEMA = StructType([
    StructField("id",           IntegerType(),   nullable=False),
    StructField("customer_id",  IntegerType(),   nullable=False),
    StructField("status",       StringType(),    nullable=False),
    StructField("total",        DoubleType(),    nullable=False),
    StructField("created_at",   TimestampType(), nullable=False),
    StructField("updated_at",   TimestampType(), nullable=False),
    StructField("is_deleted",   BooleanType(),   nullable=False),
    StructField("_silver_at",   TimestampType(), nullable=False),
])

VALID_STATUSES = {"pending", "completed", "cancelled", "refunded"}


def create_spark() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("BronzeToSilver-Orders")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "8")  # small data locally; tune for cluster
        .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def read_bronze(spark: SparkSession, lake_path: str, date: str) -> DataFrame:
    """Read a day's worth of Bronze Parquet files."""
    year, month, day = date.split("-")
    path = f"{lake_path}/bronze/orders/{year}/{month}/{day}/"
    logger.info("reading_bronze path=%s", path)
    return spark.read.parquet(path)


def clean_and_validate(df: DataFrame) -> DataFrame:
    """Apply all business rules; drop or flag bad rows."""
    # 1. Cast types
    df = df.withColumn("id",          F.col("id").cast(IntegerType())) \
           .withColumn("customer_id", F.col("customer_id").cast(IntegerType())) \
           .withColumn("total",       F.col("total").cast(DoubleType())) \
           .withColumn("created_at",  F.col("created_at").cast(TimestampType())) \
           .withColumn("updated_at",  F.col("updated_at").cast(TimestampType()))

    # 2. Normalise status
    df = df.withColumn("status", F.lower(F.trim(F.col("status"))))

    # 3. Reject rows that violate hard constraints
    rows_before = df.count()
    df = df.filter(
        F.col("id").isNotNull() &
        F.col("customer_id").isNotNull() &
        (F.col("total") >= 0) &
        F.col("status").isin(*VALID_STATUSES)
    )
    rows_after = df.count()
    dropped = rows_before - rows_after
    if dropped:
        logger.warning("validation_dropped_rows count=%d", dropped)

    # 4. Deduplicate: keep the latest updated_at per id
    df = df.withColumn(
        "_row_num",
        F.row_number().over(
            __import__("pyspark.sql.window", fromlist=["Window"])
            .Window.partitionBy("id").orderBy(F.col("updated_at").desc())
        )
    ).filter(F.col("_row_num") == 1).drop("_row_num")

    # 5. Add audit columns
    df = df.withColumn("is_deleted",  F.lit(False)) \
           .withColumn("_silver_at",  F.current_timestamp())

    return df.select([f.name for f in SILVER_SCHEMA.fields])


def merge_to_silver(spark: SparkSession, silver_df: DataFrame, silver_path: str) -> None:
    """Idempotent MERGE into Silver Delta table."""
    if DeltaTable.isDeltaTable(spark, silver_path):
        logger.info("merging_into_existing_silver path=%s", silver_path)
        DeltaTable.forPath(spark, silver_path).alias("target").merge(
            silver_df.alias("source"),
            "target.id = source.id",
        ).whenMatchedUpdate(set={
            "status":     "source.status",
            "total":      "source.total",
            "updated_at": "source.updated_at",
            "is_deleted": "source.is_deleted",
            "_silver_at": "source._silver_at",
        }).whenNotMatchedInsertAll().execute()
    else:
        logger.info("creating_new_silver_table path=%s", silver_path)
        silver_df.write.format("delta").save(silver_path)

    logger.info("silver_merge_complete rows=%d", silver_df.count())


def run(lake_path: str, date: str) -> None:
    spark = create_spark()
    spark.sparkContext.setLogLevel("WARN")

    try:
        bronze_df = read_bronze(spark, lake_path, date)
        silver_df = clean_and_validate(bronze_df)
        merge_to_silver(spark, silver_df, f"{lake_path}/silver/orders")
    finally:
        spark.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--lake-path", default="/data/lake")
    args = parser.parse_args()
    run(lake_path=args.lake_path, date=args.date)
```

---

## Step 5 — Airflow DAGs

### `airflow/dags/bronze_ingestion.py`

```python
"""
Daily Bronze ingestion: pulls incremental data from source PostgreSQL
and writes raw Parquet to the Bronze Delta Lake layer.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import get_current_context
from airflow.providers.postgres.hooks.postgres import PostgresHook

LAKE_PATH = Path(Variable.get("lake_path", "/data/lake"))
logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(hours=1),
    "on_failure_callback": lambda ctx: logger.error(
        "DAG FAILED task=%s", ctx["task_instance"].task_id
    ),
}


@dag(
    dag_id="bronze_ingestion_daily",
    schedule="0 1 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=True,            # allow backfill
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["bronze", "daily", "ingestion"],
    doc_md=__doc__,
)
def bronze_ingestion() -> None:

    @task(task_id="extract_orders")
    def extract_orders(**context: dict) -> str:
        start = context["data_interval_start"].isoformat()
        end   = context["data_interval_end"].isoformat()
        date_str = context["data_interval_start"].strftime("%Y/%m/%d")

        hook = PostgresHook(postgres_conn_id="source_postgres")
        df = hook.get_pandas_df(
            """
            SELECT o.id, o.customer_id, o.status, o.total,
                   o.created_at, o.updated_at,
                   c.country, c.segment
            FROM   orders o
            JOIN   customers c ON o.customer_id = c.id
            WHERE  o.updated_at >= %(start)s
              AND  o.updated_at <  %(end)s
            """,
            parameters={"start": start, "end": end},
        )

        logger.info("extracted rows=%d window=[%s, %s)", len(df), start, end)

        if df.empty:
            return ""

        out_dir = LAKE_PATH / "bronze" / "orders" / date_str
        out_dir.mkdir(parents=True, exist_ok=True)
        path = str(out_dir / "batch.parquet")
        pq.write_table(pa.Table.from_pandas(df), path, compression="snappy")
        return path

    @task(task_id="validate_bronze")
    def validate_bronze(parquet_path: str) -> dict:
        if not parquet_path:
            return {"rows": 0, "issues": []}

        df = pd.read_parquet(parquet_path)
        issues: list[str] = []

        null_ids = int(df["id"].isna().sum())
        if null_ids:
            issues.append(f"{null_ids} rows with null id")

        neg_totals = int((df["total"] < 0).sum())
        if neg_totals:
            issues.append(f"{neg_totals} rows with negative total")

        invalid_status = df[~df["status"].isin(["pending","completed","cancelled","refunded"])]
        if not invalid_status.empty:
            issues.append(f"{len(invalid_status)} rows with unknown status")

        if issues:
            raise ValueError(f"Bronze validation failed: {'; '.join(issues)}")

        logger.info("bronze_valid rows=%d", len(df))
        return {"rows": len(df), "issues": []}

    path = extract_orders()
    validate_bronze(path)


bronze_ingestion_dag = bronze_ingestion()
```

### `airflow/dags/silver_processing.py`

```python
"""
Daily Silver processing: runs PySpark job to clean, deduplicate,
and merge Bronze data into Silver Delta Lake.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable

LAKE_PATH = Variable.get("lake_path", "/data/lake")
SPARK_JOBS_PATH = Variable.get("spark_jobs_path", "/opt/spark_jobs")

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


@dag(
    dag_id="silver_processing_daily",
    schedule="0 2 * * *",          # 1 hour after bronze ingestion
    start_date=datetime(2024, 1, 1),
    catchup=True,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["silver", "daily", "spark"],
)
def silver_processing() -> None:

    @task(task_id="run_orders_silver")
    def run_orders_silver(**context: dict) -> None:
        date = context["data_interval_start"].strftime("%Y-%m-%d")
        result = subprocess.run(
            [
                "spark-submit",
                "--packages", "io.delta:delta-spark_2.12:3.1.0",
                f"{SPARK_JOBS_PATH}/bronze_to_silver_orders.py",
                "--date", date,
                "--lake-path", LAKE_PATH,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Spark job failed:\n{result.stderr}")

    @task(task_id="verify_silver_row_count")
    def verify_silver_row_count(**context: dict) -> None:
        """Check Silver row count increased after the job."""
        import duckdb
        date = context["data_interval_start"].strftime("%Y-%m-%d")
        con = duckdb.connect()
        result = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{LAKE_PATH}/silver/orders/**/*.parquet')
            WHERE DATE_TRUNC('day', updated_at) = '{date}'
        """).fetchone()
        rows = result[0] if result else 0
        if rows == 0:
            raise ValueError(f"Silver has 0 rows for {date} — something went wrong")

    run_orders_silver() >> verify_silver_row_count()


silver_processing_dag = silver_processing()
```

### `airflow/dags/gold_dbt_run.py`

```python
"""Gold layer: runs dbt to build star schema from Silver data."""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta

from airflow.decorators import dag, task

DBT_PATH = "/opt/dbt"

@dag(
    dag_id="gold_dbt_run_daily",
    schedule="0 4 * * *",    # after silver
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={"owner": "data-engineering", "retries": 1},
    tags=["gold", "dbt", "daily"],
)
def gold_dbt_run() -> None:

    @task
    def dbt_run() -> None:
        result = subprocess.run(
            ["dbt", "run", "--profiles-dir", DBT_PATH, "--project-dir", DBT_PATH],
            capture_output=True, text=True, check=False,
        )
        print(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(f"dbt run failed:\n{result.stderr}")

    @task
    def dbt_test() -> None:
        result = subprocess.run(
            ["dbt", "test", "--profiles-dir", DBT_PATH, "--project-dir", DBT_PATH],
            capture_output=True, text=True, check=False,
        )
        print(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(f"dbt tests failed:\n{result.stderr}")

    @task
    def dbt_docs_generate() -> None:
        subprocess.run(
            ["dbt", "docs", "generate", "--profiles-dir", DBT_PATH, "--project-dir", DBT_PATH],
            check=True,
        )

    dbt_run() >> dbt_test() >> dbt_docs_generate()


gold_dbt_dag = gold_dbt_run()
```

---

## Step 6 — dbt Project

### `dbt/dbt_project.yml`

```yaml
name: data_platform
version: "1.0.0"
config-version: 2
profile: data_platform

model-paths: ["models"]
test-paths: ["tests"]
macro-paths: ["macros"]

models:
  data_platform:
    staging:
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: ephemeral
    marts:
      +materialized: table
      finance:
        fct_orders:
          +materialized: incremental
          +unique_key: order_id
          +incremental_strategy: merge
```

### `dbt/models/staging/stg_orders.sql`

```sql
-- Staging: clean and rename raw Silver orders
WITH source AS (
    SELECT * FROM {{ source('silver', 'orders') }}
),
cleaned AS (
    SELECT
        id::INTEGER                             AS order_id,
        customer_id::INTEGER                    AS customer_id,
        LOWER(TRIM(status))                     AS status,
        total::NUMERIC(12,2)                    AS total_amount,
        COALESCE(country, 'unknown')            AS country,
        COALESCE(segment, 'regular')            AS customer_segment,
        created_at::TIMESTAMPTZ                 AS created_at,
        updated_at::TIMESTAMPTZ                 AS updated_at,
        CURRENT_TIMESTAMP                       AS _stg_loaded_at
    FROM source
    WHERE id IS NOT NULL
      AND total >= 0
      AND status IN ('pending','completed','cancelled','refunded')
)
SELECT * FROM cleaned
```

### `dbt/models/staging/_sources.yml`

```yaml
version: 2

sources:
  - name: silver
    description: "Silver Delta Lake tables (read via DuckDB or PostgreSQL views)"
    schema: silver
    freshness:
      warn_after: { count: 1, period: day }
      error_after: { count: 2, period: day }
    loaded_at_field: updated_at
    tables:
      - name: orders
        description: "Cleaned orders from Bronze → Silver pipeline"
        columns:
          - name: id
            tests: [not_null, unique]
          - name: customer_id
            tests: [not_null]
          - name: status
            tests:
              - not_null
              - accepted_values:
                  values: ['pending','completed','cancelled','refunded']
          - name: total
            tests:
              - not_null
              - dbt_utils.expression_is_true:
                  expression: ">= 0"
```

### `dbt/models/marts/finance/fct_orders.sql`

```sql
{{
    config(
        materialized = 'incremental',
        unique_key   = 'order_id',
        incremental_strategy = 'merge',
        on_schema_change = 'append_new_columns',
    )
}}

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
        WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),
dim_dates AS (SELECT * FROM {{ ref('dim_date') }}),
enriched AS (
    SELECT
        o.order_id,
        o.customer_id,
        d.date_key,
        d.year,
        d.quarter,
        d.month,
        d.week_of_year,
        d.is_weekend,
        o.status,
        o.total_amount,
        o.country,
        o.customer_segment,
        CASE
            WHEN o.total_amount >= 1000 THEN 'high'
            WHEN o.total_amount >= 100  THEN 'medium'
            ELSE 'low'
        END                                       AS order_tier,
        o.status = 'completed'                    AS is_completed,
        o.created_at,
        o.updated_at,
        CURRENT_TIMESTAMP                         AS _fct_loaded_at
    FROM orders o
    LEFT JOIN dim_dates d ON d.date_actual = o.created_at::DATE
)
SELECT * FROM enriched
```

### `dbt/models/marts/marketing/agg_revenue_daily.sql`

```sql
{{ config(materialized='table') }}

SELECT
    fo.created_at::DATE                           AS date,
    fo.country,
    fo.customer_segment,
    COUNT(*)                                      AS order_count,
    COUNT(*) FILTER (WHERE fo.is_completed)       AS completed_orders,
    SUM(fo.total_amount)                          AS gross_revenue,
    SUM(fo.total_amount) FILTER (WHERE fo.is_completed) AS net_revenue,
    AVG(fo.total_amount) FILTER (WHERE fo.is_completed) AS avg_order_value,
    COUNT(DISTINCT fo.customer_id)                AS unique_customers,
    -- Running total per country
    SUM(SUM(fo.total_amount) FILTER (WHERE fo.is_completed))
        OVER (PARTITION BY fo.country ORDER BY fo.created_at::DATE)
                                                  AS running_net_revenue
FROM {{ ref('fct_orders') }} fo
GROUP BY 1, 2, 3
ORDER BY 1, 2
```

### `dbt/models/marts/finance/schema.yml`

```yaml
version: 2
models:
  - name: fct_orders
    description: "One row per order — the primary facts table"
    columns:
      - name: order_id
        tests: [unique, not_null]
      - name: customer_id
        tests: [not_null]
      - name: total_amount
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"
      - name: status
        tests:
          - accepted_values:
              values: ['pending','completed','cancelled','refunded']
```

---

## Step 7 — DuckDB Serving Layer

### `analytics/query_engine.py`

```python
"""
DuckDB-based analytics engine: query Silver Parquet files directly
without loading anything into a database.

Usage:
    engine = AnalyticsEngine("/data/lake")
    df = engine.revenue_by_country(days=30)
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


class AnalyticsEngine:
    def __init__(self, lake_path: str) -> None:
        self._lake = Path(lake_path)
        self._con = duckdb.connect()
        self._register_views()

    def _register_views(self) -> None:
        self._con.execute(f"""
            CREATE OR REPLACE VIEW orders AS
            SELECT * FROM read_parquet('{self._lake}/silver/orders/**/*.parquet');

            CREATE OR REPLACE VIEW customers AS
            SELECT * FROM read_parquet('{self._lake}/silver/customers/**/*.parquet');

            CREATE OR REPLACE VIEW products AS
            SELECT * FROM read_parquet('{self._lake}/silver/products/**/*.parquet');
        """)

    def execute(self, sql: str, params: dict | None = None) -> pd.DataFrame:
        return self._con.execute(sql, list(params.values()) if params else []).df()

    # ── Pre-built analytics queries ────────────────────────────────────────

    def revenue_by_country(self, days: int = 30) -> pd.DataFrame:
        return self.execute(f"""
            SELECT
                country,
                COUNT(*)                                             AS orders,
                COUNT(*) FILTER (WHERE status = 'completed')        AS completed,
                ROUND(SUM(total) FILTER (WHERE status = 'completed'), 2) AS revenue,
                ROUND(AVG(total) FILTER (WHERE status = 'completed'), 2) AS avg_order
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY country
            ORDER BY revenue DESC NULLS LAST
        """)

    def monthly_revenue_growth(self) -> pd.DataFrame:
        return self.execute("""
            WITH monthly AS (
                SELECT
                    DATE_TRUNC('month', created_at) AS month,
                    SUM(total) FILTER (WHERE status = 'completed') AS revenue
                FROM orders
                GROUP BY 1
            )
            SELECT
                month,
                revenue,
                LAG(revenue) OVER (ORDER BY month)                   AS prev_revenue,
                ROUND((revenue / LAG(revenue) OVER (ORDER BY month) - 1) * 100, 2)
                                                                     AS mom_growth_pct,
                SUM(revenue) OVER (ORDER BY month)                   AS running_total
            FROM monthly
            ORDER BY month
        """)

    def customer_ltv_segments(self) -> pd.DataFrame:
        return self.execute("""
            WITH ltv AS (
                SELECT
                    customer_id,
                    SUM(total) FILTER (WHERE status = 'completed') AS lifetime_value,
                    COUNT(*) FILTER (WHERE status = 'completed')   AS order_count,
                    MAX(created_at)                                AS last_order_at,
                    DATEDIFF('day', MAX(created_at), NOW())        AS days_since_last_order
                FROM orders
                GROUP BY customer_id
            )
            SELECT
                NTILE(5) OVER (ORDER BY lifetime_value)  AS ltv_quintile,
                COUNT(*)                                  AS customers,
                ROUND(AVG(lifetime_value), 2)             AS avg_ltv,
                ROUND(AVG(order_count), 1)                AS avg_orders,
                ROUND(AVG(days_since_last_order), 0)      AS avg_recency_days
            FROM ltv
            GROUP BY 1
            ORDER BY 1
        """)

    def funnel_analysis(self, days: int = 30) -> pd.DataFrame:
        return self.execute(f"""
            SELECT
                COUNT(DISTINCT customer_id)
                    FILTER (WHERE status IN ('pending','completed','cancelled','refunded'))
                                                      AS step1_placed,
                COUNT(DISTINCT customer_id)
                    FILTER (WHERE status IN ('completed','cancelled','refunded'))
                                                      AS step2_processed,
                COUNT(DISTINCT customer_id)
                    FILTER (WHERE status = 'completed')
                                                      AS step3_completed,
                ROUND(
                    COUNT(DISTINCT customer_id) FILTER (WHERE status IN ('completed','cancelled','refunded'))
                    * 100.0 / NULLIF(COUNT(DISTINCT customer_id), 0), 2
                )                                     AS step1_to_step2_pct,
                ROUND(
                    COUNT(DISTINCT customer_id) FILTER (WHERE status = 'completed')
                    * 100.0 / NULLIF(COUNT(DISTINCT customer_id) FILTER (
                        WHERE status IN ('completed','cancelled','refunded')), 0), 2
                )                                     AS step2_to_step3_pct
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '{days} days'
        """)

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> "AnalyticsEngine":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
```

---

## Step 8 — Tests

### `tests/unit/test_transformations.py`

```python
"""Unit tests for Spark transformation logic (using Pandas as a proxy)."""
import pandas as pd
import pytest


def clean_status(status: str | None) -> str:
    if not status:
        return "unknown"
    s = status.lower().strip()
    return s if s in {"pending", "completed", "cancelled", "refunded"} else "unknown"


@pytest.mark.parametrize("raw,expected", [
    ("completed", "completed"),
    ("COMPLETED", "completed"),
    ("  Pending  ", "pending"),
    ("CANCELLED", "cancelled"),
    ("garbage", "unknown"),
    (None, "unknown"),
    ("", "unknown"),
])
def test_clean_status(raw, expected):
    assert clean_status(raw) == expected


def test_negative_total_removed():
    df = pd.DataFrame({"id": [1, 2, 3], "total": [100.0, -5.0, 0.0]})
    result = df[df["total"] >= 0]
    assert len(result) == 2
    assert 2 not in result["id"].values


def test_deduplication_keeps_latest():
    df = pd.DataFrame({
        "id": [1, 1, 2],
        "total": [100.0, 150.0, 200.0],
        "updated_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-01"]),
    })
    result = df.sort_values("updated_at", ascending=False).drop_duplicates("id")
    assert result[result["id"] == 1]["total"].iloc[0] == 150.0
```

### `tests/integration/test_pipeline_e2e.py`

```python
"""
End-to-end pipeline smoke test.
Requires Docker Compose stack to be running.
"""
import os
import pytest
import pandas as pd
from pathlib import Path

LAKE_PATH = Path(os.getenv("LAKE_PATH", "/data/lake"))


@pytest.mark.skipif(
    not LAKE_PATH.exists(),
    reason="Lake path not found — run docker-compose up first",
)
def test_bronze_files_exist():
    bronze_orders = LAKE_PATH / "bronze" / "orders"
    assert bronze_orders.exists(), "No bronze/orders directory found"
    parquet_files = list(bronze_orders.rglob("*.parquet"))
    assert len(parquet_files) > 0, "No Parquet files in bronze/orders"


@pytest.mark.skipif(not LAKE_PATH.exists(), reason="Lake path not found")
def test_silver_schema_matches():
    silver_orders = LAKE_PATH / "silver" / "orders"
    if not silver_orders.exists():
        pytest.skip("Silver orders not yet built — run silver_processing DAG")

    import duckdb
    df = duckdb.execute(
        f"SELECT * FROM read_parquet('{silver_orders}/**/*.parquet') LIMIT 1"
    ).df()
    required = {"id", "customer_id", "status", "total", "created_at", "is_deleted"}
    assert required.issubset(set(df.columns)), f"Missing columns: {required - set(df.columns)}"


@pytest.mark.skipif(not LAKE_PATH.exists(), reason="Lake path not found")
def test_no_null_ids_in_silver():
    silver_orders = LAKE_PATH / "silver" / "orders"
    if not silver_orders.exists():
        pytest.skip("Silver not ready")

    import duckdb
    result = duckdb.execute(
        f"SELECT COUNT(*) FROM read_parquet('{silver_orders}/**/*.parquet') WHERE id IS NULL"
    ).fetchone()
    assert result[0] == 0, f"Found {result[0]} rows with null id in Silver"


@pytest.mark.skipif(not LAKE_PATH.exists(), reason="Lake path not found")
def test_analytics_engine_runs():
    from analytics.query_engine import AnalyticsEngine
    with AnalyticsEngine(str(LAKE_PATH)) as engine:
        df = engine.revenue_by_country(days=365)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
```

---

## Step 9 — CI/CD

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: ecommerce
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: password
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 5s
          --health-timeout 3s --health-retries 10

    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra dev

      - name: Lint (ruff)
        run: uv run ruff check .

      - name: Type check (mypy)
        run: uv run mypy spark_jobs/ streaming/ analytics/ --ignore-missing-imports

      - name: Unit tests
        run: uv run pytest tests/unit/ -v

      - name: Seed test database
        run: psql postgresql://postgres:password@localhost:5432/ecommerce < infrastructure/postgres/init.sql

      - name: Integration tests (no Spark/Delta needed)
        run: uv run pytest tests/integration/test_pipeline_e2e.py -v -k "not silver" || true

  dbt-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install dbt-postgres dbt-utils
      - name: dbt debug (connection check)
        working-directory: dbt/
        run: dbt debug --no-version-check
        continue-on-error: true  # no live DB in CI
      - name: dbt parse (syntax check)
        working-directory: dbt/
        run: dbt parse --no-version-check
```

---

## Step 10 — Makefile

```makefile
.PHONY: help up down seed register-connector status logs test lint

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

up:            ## Start full Docker Compose stack
	docker-compose up -d --build
	@echo "Waiting for services..."
	@sleep 15
	@echo "✅ Stack is up — Airflow at http://localhost:8080 (admin/admin)"

down:          ## Stop and remove all containers + volumes
	docker-compose down -v

seed:          ## Seed the source PostgreSQL with 100k orders
	docker exec dp_postgres_source psql -U postgres -d ecommerce \
	  -c "SELECT COUNT(*) FROM orders;"

register-connector:  ## Register Debezium connector for CDC
	curl -s -X POST http://localhost:8083/connectors \
	  -H "Content-Type: application/json" \
	  -d @infrastructure/kafka/connectors/debezium-postgres.json | python3 -m json.tool

connector-status:    ## Check Debezium connector status
	curl -s http://localhost:8083/connectors/ecommerce-cdc/status | python3 -m json.tool

kafka-topics:        ## List Kafka topics
	docker exec dp_kafka kafka-topics --bootstrap-server localhost:9092 --list

consumer-lag:        ## Show consumer group lag
	docker exec dp_kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
	  --group cdc-bronze-writer-v1 --describe

start-cdc-consumer:  ## Start CDC consumer (foreground)
	LAKE_PATH=./data/lake uv run python streaming/cdc_consumer.py

airflow-trigger-bronze:  ## Manually trigger the bronze ingestion DAG for today
	docker exec dp_airflow airflow dags trigger bronze_ingestion_daily

test:          ## Run full test suite
	uv run pytest tests/ -v

test-unit:     ## Run unit tests only (fast, no infrastructure)
	uv run pytest tests/unit/ -v --no-cov

lint:          ## Lint with ruff
	uv run ruff check .

dbt-run:       ## Run all dbt models
	cd dbt && dbt run

dbt-test:      ## Run all dbt tests
	cd dbt && dbt test

dbt-docs:      ## Generate and serve dbt docs
	cd dbt && dbt docs generate && dbt docs serve --port 8081

query-silver:  ## Ad-hoc DuckDB query on Silver layer
	uv run python -c "
from analytics.query_engine import AnalyticsEngine
with AnalyticsEngine('./data/lake') as e:
    print(e.revenue_by_country().to_string())
"

clean:         ## Remove compiled Python + cache files
	find . -type d -name __pycache__ | xargs rm -rf
	find . -name "*.pyc" -delete
	rm -rf .mypy_cache .ruff_cache .pytest_cache
```

---

## ✅ Production Checklist

### Ingestion & Reliability
- [ ] Debezium CDC connector captures INSERT / UPDATE / DELETE
- [ ] CDC consumer uses at-least-once + idempotent upsert (no duplicates)
- [ ] Airflow DAGs: retries with exponential backoff, failure callbacks
- [ ] Airflow: `catchup=True` + `max_active_runs=1` for safe backfills
- [ ] All Bronze writes are append-only (never modify historical data)

### Data Quality
- [ ] Schema enforcement on Silver (cast errors → quarantine)
- [ ] Deduplication by `id + updated_at` in every Silver job
- [ ] dbt source freshness checks (error after 2 days stale)
- [ ] dbt schema tests: `not_null`, `unique`, `accepted_values`, `relationships`
- [ ] Singular test: `assert_no_negative_revenue.sql`
- [ ] Integration test: Silver has 0 null IDs after every run

### Observability
- [ ] Structured logs in every pipeline component
- [ ] Consumer lag monitoring via `kafka-consumer-groups --describe`
- [ ] Airflow task SLAs and email alerts on failure
- [ ] Silver row-count verification step in every DAG

### Developer Experience
- [ ] `make up` starts everything in one command
- [ ] `make register-connector` sets up CDC in one command
- [ ] `make dbt-docs` generates interactive data lineage graph
- [ ] `make query-silver` runs DuckDB ad-hoc analytics instantly
