# Pillar 5 — ETL / ELT Pipelines

> **Duration:** 2 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Understand ETL vs ELT and when to use each
- Build production pipelines with Apache Airflow
- Write dbt models for in-warehouse transformations
- Implement incremental loads, idempotent pipelines, and backfills
- Handle pipeline failures: retries, alerting, dead-letter queues
- Extract data from APIs, databases, and files

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [Airflow Official Docs](https://airflow.apache.org/docs/) | 📄 Docs | ✅ Free |
| [dbt Official Docs](https://docs.getdbt.com/) | 📄 Docs | ✅ Free |
| [dbt Learn — Free courses](https://learn.getdbt.com/) | 🏥 Course | ✅ Free |
| [The Data Engineering Cookbook — GitHub](https://github.com/andkret/Cookbook) | 📄 Free PDF | ✅ Free |
| [Start Data Engineering — Pipeline Patterns](https://www.startdataengineering.com/post/design-patterns-modern-data-pipelines/) | 📄 Article | ✅ Free |
| [Astronomer Airflow Guides](https://www.astronomer.io/docs/learn/) | 📄 Guides | ✅ Free |

> 💡 **Optional paid book:** *Fundamentals of Data Engineering* — Reis & Housley (O'Reilly)

---

## Section 1 — ETL vs ELT

```
ETL (Extract → Transform → Load)   — Traditional
  Source → [Transform in pipeline code] → Data Warehouse
  When to use:
    - Transformations need external logic (ML models, complex business rules)
    - Sensitive data must be masked before loading
    - Warehouse is expensive per-query (avoid loading garbage)

ELT (Extract → Load → Transform)   — Modern (cloud DW era)
  Source → Data Warehouse (raw) → [Transform using SQL/dbt]
  When to use:
    - Cheap cloud storage (store everything raw)
    - Warehouse is powerful enough to transform at scale
    - SQL-based transformations (dbt)
    - Need to reprocess historical data with new logic
```

### Pipeline Properties to Always Design For

```
Idempotency   → running a pipeline twice = same result as running it once
               (no duplicates, no data loss)

Incremental   → only process new/changed data (not full reload every time)

Backfillable  → can re-run a pipeline for a past time range

Observable    → logs, metrics, alerting on failures

Testable      → unit tests for transformation logic
```

---

## Section 2 — Apache Airflow

Airflow is the most widely-used workflow orchestration tool for data engineering.

### Core Concepts

```
DAG        — Directed Acyclic Graph; defines the pipeline structure
Task       — a single unit of work (a node in the DAG)
Operator   — a type of task (PythonOperator, BashOperator, SQLOperator...)
TaskFlow   — modern API using @task decorator
Schedule   — cron expression or timedelta for when to run
Run        — one execution of a DAG for a specific logical_date
XCom       — mechanism for tasks to pass data to each other
```

### Modern Airflow (TaskFlow API)

```python
# dags/ecommerce_etl.py
from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.operators.email import EmailOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import requests


DEFAULT_ARGS = {
    "owner": "data-team",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(hours=1),
    "email_on_failure": True,
    "email": ["data-alerts@company.com"],
}


@dag(
    dag_id="ecommerce_daily_etl",
    description="Daily ETL: extract orders from API, load to DW",
    schedule="0 3 * * *",          # 3 AM UTC every day
    start_date=datetime(2024, 1, 1),
    catchup=False,                  # don't backfill past runs on deploy
    max_active_runs=1,              # only one run at a time
    default_args=DEFAULT_ARGS,
    tags=["ecommerce", "daily"],
)
def ecommerce_daily_etl():

    @task()
    def extract_orders(logical_date=None) -> dict:
        """Extract orders from source API for a given date."""
        date_str = logical_date.strftime("%Y-%m-%d")
        response = requests.get(
            f"https://api.ecommerce.com/orders",
            params={"date": date_str, "per_page": 1000},
            headers={"Authorization": "Bearer {{var.value.api_token}}"},
            timeout=30,
        )
        response.raise_for_status()
        orders = response.json()["orders"]
        print(f"Extracted {len(orders)} orders for {date_str}")
        return {"orders": orders, "date": date_str, "count": len(orders)}

    @task()
    def validate_orders(extracted: dict) -> dict:
        """Validate extracted data quality."""
        orders = extracted["orders"]
        errors = []

        for order in orders:
            if not order.get("id"):
                errors.append(f"Missing id: {order}")
            if order.get("total", 0) < 0:
                errors.append(f"Negative total: {order['id']}")

        if errors:
            raise ValueError(f"Validation failed: {errors[:5]}")

        # Check completeness
        if len(orders) == 0:
            raise ValueError(f"No orders extracted for {extracted['date']}")

        print(f"Validated {len(orders)} orders — all pass")
        return extracted

    @task()
    def transform_orders(validated: dict) -> list[dict]:
        """Transform and clean order data."""
        orders = validated["orders"]
        transformed = []
        for order in orders:
            transformed.append({
                "id": order["id"],
                "customer_id": order["customer"]["id"],
                "status": order["status"].lower().strip(),
                "total": round(float(order["total"]), 2),
                "created_at": order["created_at"],
                "source": order.get("source", "web"),
                "etl_loaded_at": datetime.utcnow().isoformat(),
            })
        return transformed

    @task()
    def load_orders(transformed: list[dict]) -> int:
        """Upsert orders into PostgreSQL data warehouse."""
        hook = PostgresHook(postgres_conn_id="data_warehouse")
        conn = hook.get_conn()
        cursor = conn.cursor()

        # Idempotent UPSERT
        cursor.executemany("""
            INSERT INTO stg_orders (id, customer_id, status, total, created_at, source, etl_loaded_at)
            VALUES (%(id)s, %(customer_id)s, %(status)s, %(total)s, %(created_at)s, %(source)s, %(etl_loaded_at)s)
            ON CONFLICT (id) DO UPDATE
                SET status        = EXCLUDED.status,
                    total         = EXCLUDED.total,
                    etl_loaded_at = EXCLUDED.etl_loaded_at
        """, transformed)
        conn.commit()
        cursor.close()
        print(f"Upserted {len(transformed)} orders")
        return len(transformed)

    @task()
    def update_metrics(row_count: int, logical_date=None) -> None:
        """Record pipeline metrics."""
        hook = PostgresHook(postgres_conn_id="data_warehouse")
        hook.run("""
            INSERT INTO pipeline_runs (dag_id, run_date, rows_loaded, finished_at)
            VALUES ('ecommerce_daily_etl', %s, %s, NOW())
        """, parameters=(logical_date, row_count))

    # DAG dependency chain
    extracted = extract_orders()
    validated = validate_orders(extracted)
    transformed = transform_orders(validated)
    row_count = load_orders(transformed)
    update_metrics(row_count)


ecommerce_etl_dag = ecommerce_daily_etl()
```

### Incremental Loads — The Most Important Pattern

```python
@task()
def extract_incremental(logical_date=None, **context) -> dict:
    """
    Incremental extraction: only get new records since last successful run.
    Uses data_interval_start and data_interval_end for the window.
    """
    start = context["data_interval_start"]  # start of this run's window
    end   = context["data_interval_end"]    # end of this run's window

    hook = PostgresHook(postgres_conn_id="source_db")
    df = hook.get_pandas_df("""
        SELECT *
        FROM orders
        WHERE updated_at >= %(start)s
          AND updated_at <  %(end)s
    """, parameters={"start": start, "end": end})

    print(f"Incremental window: {start} → {end}, rows: {len(df)}")
    return df.to_dict("records")
```

### Backfilling

```bash
# Run pipeline for a historical date range
airflow dags backfill \
    --start-date 2024-01-01 \
    --end-date 2024-03-31 \
    ecommerce_daily_etl

# Reset specific runs
airflow tasks clear -s 2024-01-15 -e 2024-01-15 ecommerce_daily_etl
```

### Dynamic DAGs

```python
# Generate multiple DAGs from config
PIPELINES = [
    {"name": "orders", "table": "orders", "schedule": "0 3 * * *"},
    {"name": "products", "table": "products", "schedule": "0 4 * * 0"},
    {"name": "customers", "table": "customers", "schedule": "0 5 * * *"},
]

def create_dag(config: dict):
    @dag(
        dag_id=f"sync_{config['name']}",
        schedule=config["schedule"],
        start_date=datetime(2024, 1, 1),
        catchup=False,
    )
    def pipeline():
        @task
        def extract(): ...
        @task
        def load(): ...
        load(extract())

    return pipeline()

for cfg in PIPELINES:
    globals()[f"dag_{cfg['name']}"] = create_dag(cfg)
```

---

## Section 3 — dbt (Data Build Tool)

dbt runs SQL-based **transformations inside your data warehouse**.
It's the T in ELT.

### Project Structure

```
my_dbt_project/
├── dbt_project.yml          # project config
├── profiles.yml             # connection config
├── models/
│   ├── staging/             # raw → clean (1:1 with source tables)
│   │   ├── stg_orders.sql
│   │   ├── stg_customers.sql
│   │   └── _sources.yml     # define source tables
│   ├── intermediate/        # complex joins/transformations
│   │   └── int_orders_with_customers.sql
│   └── marts/               # final analytics-ready tables
│       ├── finance/
│       │   └── fct_orders.sql
│       └── marketing/
│           └── dim_customers.sql
├── tests/
│   ├── generic/             # reusable test macros
│   └── singular/            # specific SQL tests
├── macros/                  # reusable SQL macros (Jinja)
└── seeds/                   # small CSV reference data
```

### Staging Model

```sql
-- models/staging/stg_orders.sql
-- Clean and rename raw data

WITH source AS (
    SELECT * FROM {{ source('ecommerce', 'raw_orders') }}
),
renamed AS (
    SELECT
        id::INTEGER                              AS order_id,
        customer_id::INTEGER                     AS customer_id,
        LOWER(TRIM(status))                      AS status,
        total::NUMERIC(10, 2)                    AS total_amount,
        created_at::TIMESTAMPTZ                  AS created_at,
        updated_at::TIMESTAMPTZ                  AS updated_at,
        COALESCE(LOWER(source), 'unknown')       AS acquisition_source,
        -- audit columns
        CURRENT_TIMESTAMP                        AS dbt_loaded_at
    FROM source
    WHERE id IS NOT NULL
      AND total >= 0
)
SELECT * FROM renamed
```

### Incremental Model

```sql
-- models/marts/finance/fct_orders.sql
-- Incremental: only process new/updated rows

{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',  -- or 'insert_overwrite', 'delete+insert'
        on_schema_change='append_new_columns',
    )
}}

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
        -- Only process rows updated since last run
        WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),
customers AS (
    SELECT * FROM {{ ref('stg_customers') }}
),
enriched AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.full_name        AS customer_name,
        c.country          AS customer_country,
        c.segment          AS customer_segment,
        o.status,
        o.total_amount,
        o.acquisition_source,
        o.created_at,
        -- Derived metrics
        CASE
            WHEN o.total_amount >= 1000 THEN 'high_value'
            WHEN o.total_amount >= 100  THEN 'medium_value'
            ELSE 'low_value'
        END AS order_tier,
        EXTRACT(DOW FROM o.created_at) = 0 AS is_weekend_order
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.customer_id
)
SELECT * FROM enriched
```

### dbt Tests

```yaml
# models/staging/_sources.yml
version: 2

sources:
  - name: ecommerce
    database: my_database
    schema: raw
    tables:
      - name: raw_orders
        columns:
          - name: id
            tests:
              - not_null
              - unique
          - name: status
            tests:
              - not_null
              - accepted_values:
                  values: ['pending', 'completed', 'cancelled', 'refunded']
          - name: total
            tests:
              - not_null
              - dbt_utils.expression_is_true:
                  expression: ">= 0"

# models/marts/_models.yml
version: 2
models:
  - name: fct_orders
    description: "One row per order with enriched customer data"
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: customer_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id
```

### Macros (Reusable SQL)

```sql
-- macros/generate_surrogate_key.sql
{% macro generate_surrogate_key(fields) %}
    MD5(CONCAT_WS('|',
        {% for field in fields %}
            COALESCE(CAST({{ field }} AS TEXT), '_null_')
            {% if not loop.last %}, {% endif %}
        {% endfor %}
    ))
{% endmacro %}

-- Usage in a model:
SELECT
    {{ generate_surrogate_key(['order_id', 'product_id']) }} AS order_item_key,
    order_id,
    product_id
FROM order_items
```

```bash
# dbt commands
dbt run                             # run all models
dbt run --select fct_orders         # run one model
dbt run --select staging.*          # run all staging models
dbt run --select +fct_orders        # run fct_orders + all its dependencies
dbt test                            # run all tests
dbt docs generate && dbt docs serve # generate lineage graph
dbt debug                           # test connection
```

---

## Section 4 — Extracting from APIs with Python

```python
# extractors/api_extractor.py
import time
import logging
import requests
from dataclasses import dataclass
from typing import Iterator

logger = logging.getLogger(__name__)

@dataclass
class PaginatedExtractor:
    base_url: str
    api_key: str
    page_size: int = 100
    max_retries: int = 3
    backoff_factor: float = 2.0

    def _get_page(self, endpoint: str, params: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(
                    url,
                    params=params,
                    headers={"X-API-Key": self.api_key},
                    timeout=30,
                )
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                sleep_time = self.backoff_factor ** attempt
                logger.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {sleep_time}s")
                time.sleep(sleep_time)

    def extract_all(self, endpoint: str, filters: dict = {}) -> Iterator[dict]:
        """Extract all pages from a paginated API."""
        page = 1
        total_records = 0

        while True:
            params = {"page": page, "per_page": self.page_size, **filters}
            data = self._get_page(endpoint, params)

            records = data.get("data", [])
            if not records:
                break

            yield from records
            total_records += len(records)

            # Check pagination
            if len(records) < self.page_size:
                break  # last page
            if data.get("pagination", {}).get("has_next") is False:
                break

            page += 1
            time.sleep(0.1)  # rate limit protection

        logger.info(f"Extracted {total_records} records from {endpoint}")
```

---

## 🏋️ Exercises

### Exercise 1 — Airflow DAG
Build a DAG that:
- Extracts data from [JSONPlaceholder API](https://jsonplaceholder.typicode.com/)
- Validates required fields are present
- Loads to PostgreSQL with upsert
- Runs daily, handles retries, sends email on failure

### Exercise 2 — Incremental dbt Model
Build a dbt project with:
- Staging models for orders + customers
- An incremental `fct_orders` model
- Schema tests: not_null, unique, accepted_values, relationships
- Docs with model descriptions

### Exercise 3 — Pipeline Idempotency Test
Run your Airflow DAG for the same date twice.
Verify the target table has the same number of rows (upsert, not append).

---

## ✅ Self-Check Questions

1. What is the difference between ETL and ELT?
2. What does idempotency mean for a pipeline?
3. What is Airflow's `data_interval_start`?
4. What does `catchup=False` do?
5. What is an incremental dbt model?
6. What is `{{ ref() }}` in dbt?
7. What is a dbt source test?
8. How does `ON CONFLICT DO UPDATE` enable idempotent loads?
9. What is XCom in Airflow?
10. When would you use a full refresh vs incremental load?

---

## 🔗 Key Links

- https://airflow.apache.org/docs/apache-airflow/stable/
- https://docs.getdbt.com/docs/introduction
- https://www.startdataengineering.com/post/design-patterns-modern-data-pipelines/
