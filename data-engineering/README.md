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

## 📚 Must-Have Books

| Book | Covers |
|------|--------|
| *Learning SQL 3rd Ed* — Alan Beaulieu | SQL fundamentals to advanced |
| *SQL Performance Explained* — Markus Winand | Index internals, query optimization |
| *Designing Data-Intensive Applications* — Martin Kleppmann | The bible of data engineering |
| *Fundamentals of Data Engineering* — Reis & Housley | ETL, pipelines, modern data stack |
| *Learning Spark 2nd Ed* — Chambers & Zaharia | PySpark end-to-end |
| *Kafka: The Definitive Guide 2nd Ed* — Shapira et al. | Kafka deep dive |

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
