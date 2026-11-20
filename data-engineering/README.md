# 🏗️ Data Engineering Mastery — Complete Learning Guide

> Covers the full job requirement:
> *ETL/ELT pipelines · batch and streaming data · large-scale data processing ·
> PostgreSQL · MySQL · analytical/columnar stores · SQL · query optimization*

---

## 🗺️ 9 Pillars

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

**Total: ~15 weeks part-time (2–3 hrs/day)**

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
> *Learning SQL* (Beaulieu), *SQL Performance Explained* (Winand)

---

## 🏗️ Capstone — End-to-End Data Platform

An e-commerce analytics platform that:
- Ingests raw orders/events from Kafka (streaming)
- Runs nightly Spark batch jobs to aggregate data
- Stores results in PostgreSQL + Parquet/DuckDB
- Orchestrates all jobs with Apache Airflow
- Exposes metrics via SQL views and dbt models

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
