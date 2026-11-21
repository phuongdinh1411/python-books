# 🏗️ Data Engineering Mastery — Production-Grade Course

> Build the complete skill set for a Senior Data Engineer:
> *SQL mastery · PostgreSQL internals · query optimization · columnar analytics ·
> ETL/ELT with Airflow + dbt · Spark batch · Kafka streaming · Delta Lake ·
> end-to-end capstone platform · Delta Lake vs Apache Iceberg*

---

## 🎯 What You Will Build

By the end of this course you will have built and can demo:

| Deliverable | Skills Demonstrated |
|-------------|--------------------|
| SQL analytics portfolio (cohorts, funnels, RFM, retention) | Advanced SQL, window functions |
| PostgreSQL-tuned schema with indexes + partitioning | DB internals, EXPLAIN ANALYZE |
| Airflow + dbt ELT pipeline with incremental models | Pipeline orchestration, data modeling |
| PySpark batch job reading/writing Delta Lake | Distributed processing, data lakes |
| Kafka producer + consumer with idempotent upsert | Streaming, at-least-once semantics |
| **Full capstone**: Bronze → Silver → Gold data platform | All pillars combined |

---

## 🧭 Entry Points by Experience Level

| Your background | Start here |
|-----------------|------------|
| New to data engineering | Pillar 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → Capstone |
| Know SQL, new to pipelines | Pillar 3 (skim) → 4 → 5 → 6 → 7 |
| Know Spark, weak on SQL/DB | Pillar 1 → 2 → 3 → then Capstone |
| Interviewing soon | Pillars 1, 2, 3, 5 → Capstone → Pillar 10 |

---

## 🗺️ 10 Pillars

| # | Pillar | Folder | Effort |
|---|--------|--------|--------|
| 1 | SQL Fundamentals & Advanced SQL | `01-sql-fundamentals/` | 2 weeks |
| 2 | PostgreSQL Deep Dive | `02-postgresql-deep-dive/` | 2 weeks |
| 3 | Query Optimization | `03-query-optimization/` | 1 week |
| 4 | Analytical & Columnar Stores | `04-analytical-stores/` | 1 week |
| 5 | ETL / ELT Pipelines (Airflow, dbt) | `05-etl-elt-pipelines/` | 2 weeks |
| 6 | Batch Processing (Spark, Polars) | `06-batch-processing/` | 2 weeks |
| 7 | Streaming Data (Kafka, Flink) | `07-streaming-data/` | 2 weeks |
| 8 | Large-Scale Data Processing | `08-large-scale-processing/` | 1 week |
| 9 | 🏗️ Capstone — Full Data Platform | `09-capstone/` | 2 weeks |
| 10 | Delta Lake vs Apache Iceberg | `10-databricks-vs-iceberg/` | 1 week |

**Total: ~16 weeks part-time (2–3 hrs/day)**

---

## 📅 Master Schedule

```
Week 01–02 → 01 SQL Fundamentals & Advanced SQL
Week 03–04 → 02 PostgreSQL Deep Dive
Week 05    → 03 Query Optimization
Week 06    → 04 Analytical & Columnar Stores
Week 07–08 → 05 ETL/ELT Pipelines
Week 09–10 → 06 Batch Processing
Week 11–12 → 07 Streaming Data
Week 13    → 08 Large-Scale Data Processing
Week 14–15 → 09 Capstone Project
Week 16    → 10 Delta Lake vs Apache Iceberg
```

---

## ✅ Progress Tracker

- [ ] 01 SQL Fundamentals & Advanced SQL
- [ ] 02 PostgreSQL Deep Dive
- [ ] 03 Query Optimization
- [ ] 04 Analytical & Columnar Stores
- [ ] 05 ETL / ELT Pipelines
- [ ] 06 Batch Processing
- [ ] 07 Streaming Data
- [ ] 08 Large-Scale Data Processing
- [ ] 09 Capstone — End-to-End Data Platform
- [ ] 10 Delta Lake vs Apache Iceberg

---

## 📚 Free Core Resources

| Resource | Covers | Link |
|----------|--------|------|
| PostgreSQL Official Docs | SQL, indexes, internals | https://www.postgresql.org/docs/current/ |
| [SQLZoo](https://sqlzoo.net/) | SQL from basics to advanced | https://sqlzoo.net/ |
| [Mode SQL Tutorial](https://mode.com/sql-tutorial/) | Analytics SQL | https://mode.com/sql-tutorial/ |
| [pgexercises.com](https://pgexercises.com/) | PostgreSQL exercises | https://pgexercises.com/ |
| [use-the-index-luke.com](https://use-the-index-luke.com/) | Index internals, query optimization (same author as *SQL Performance Explained*) | https://use-the-index-luke.com/ |
| [*Learning Spark 2nd Ed*](https://www.databricks.com/resources/ebook/learning-spark-lightning-fast-data-analytics) | PySpark end-to-end | Free PDF via Databricks |
| [*Kafka: The Definitive Guide 2nd Ed*](https://www.confluent.io/resources/kafka-the-definitive-guide-v2/) | Kafka deep dive | Free PDF via Confluent |
| [*Architecture Patterns with Python*](https://www.cosmicpython.com/) | ETL patterns, testing | https://www.cosmicpython.com/ |
| [*The Data Engineering Cookbook*](https://github.com/andkret/Cookbook) | ETL, pipelines, modern stack | Free PDF on GitHub |
| [Airflow Official Docs](https://airflow.apache.org/docs/) | Pipeline orchestration | https://airflow.apache.org/docs/ |
| [dbt Official Docs](https://docs.getdbt.com/) | ELT transformations | https://docs.getdbt.com/ |
| [Confluent Developer](https://developer.confluent.io/) | Kafka courses & tutorials | https://developer.confluent.io/ |
| [Delta Lake Docs](https://docs.delta.io/) | ACID data lakes | https://docs.delta.io/ |
| [DuckDB Docs](https://duckdb.org/docs/) | Local analytics | https://duckdb.org/docs/ |

> 💡 **Optional paid books** (excellent if available via library/O'Reilly trial):
> *Designing Data-Intensive Applications* (Kleppmann), *Fundamentals of Data Engineering* (Reis & Housley),
> *Learning SQL* (Beaulieu), *SQL Performance Explained* (Winand),
> *Apache Iceberg: The Definitive Guide* (free PDF at iceberg.apache.org)

---

## 🏗️ Capstone — End-to-End Data Platform

An e-commerce analytics platform that:
- Ingests raw orders/events from Kafka (streaming) **and** batch API pulls via Airflow
- Cleans and deduplicates into a Bronze/Silver/Gold Delta Lake
- Runs nightly PySpark batch jobs to aggregate data
- Runs dbt incremental models to build a star schema in PostgreSQL
- Orchestrates all jobs with Apache Airflow (TaskFlow API, retries, alerting)
- Serves ad-hoc analytics via DuckDB directly on Parquet files
- Includes unit tests, integration tests, and a CI workflow

See [09-capstone/README.md](09-capstone/README.md) for the full implementation.

---

## 🛠️ Local Dev Setup (All Pillars)

```bash
# Prerequisites: Docker, Python 3.11+, uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone <your-repo> && cd data-engineering
uv init && uv add duckdb polars pandas pyarrow sqlalchemy psycopg2-binary \
    apache-airflow confluent-kafka delta-spark pyspark dbt-postgres \
    great-expectations pytest ruff mypy

# Start PostgreSQL for SQL pillars 1–3
docker run -d --name de_postgres \
  -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:16

# Full capstone stack (pillars 5–9)
cd 09-capstone && docker-compose up -d
```

---

## 🔑 The Big Picture

```
                    ┌─────────────────────────────────────────────┐
                    │           DATA SOURCES                       │
                    │  Web events · DB changes · Files · APIs      │
                    └────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
         STREAMING           BATCH               MICRO-BATCH
         (Kafka)          (Files/DB)          (Spark Streaming)
              │                  │                   │
              └──────────────────┼───────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     PROCESSING LAYER     │
                    │  Spark · dbt · Polars    │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
         DATA LAKE          DATA WAREHOUSE       OLTP DB
         (Parquet/          (Snowflake/          (PostgreSQL)
          DeltaLake)         BigQuery/DuckDB)
              │                  │                   │
              └──────────────────┼───────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    SERVING LAYER         │
                    │  SQL · APIs · Dashboards │
                    └─────────────────────────┘
```
