# 🐍 Python Mastery — Production-Grade Course

> A structured, hands-on curriculum to reach advanced Python proficiency
> as required for senior/staff Python engineering roles.

---

## 🎯 Goal

Master all skills listed in the job requirement:
> *Python internals, concurrency (asyncio, threading, multiprocessing), performance profiling,
> packaging, FastAPI/Flask, SQLAlchemy, pytest, mypy/type annotations*

---

## 📂 Structure

| # | Pillar | Folder | Effort |
|---|--------|--------|--------|
| 1 | Python Internals | `01-python-internals/` | 2 weeks |
| 2 | Concurrency | `02-concurrency/` | 3 weeks |
| 3 | Performance Profiling | `03-performance-profiling/` | 1 week |
| 4 | Packaging | `04-packaging/` | 1 week |
| 5 | FastAPI & Flask | `05-fastapi-flask/` | 2 weeks |
| 6 | SQLAlchemy & Alembic | `06-sqlalchemy/` | 2 weeks |
| 7 | pytest | `07-pytest/` | 1 week |
| 8 | mypy & Type Annotations | `08-mypy-type-annotations/` | 1 week |
| 9 | 🏗️ Capstone Project | `09-capstone/` | 2 weeks |

**Total: ~15 weeks part-time (2–3 hrs/day)**

---

## 📅 Master Schedule

```
Week 01–02 → 01 Python Internals
Week 03–05 → 02 Concurrency
Week 06    → 03 Performance Profiling
Week 07    → 04 Packaging
Week 08–09 → 05 FastAPI & Flask
Week 10–11 → 06 SQLAlchemy & Alembic
Week 12    → 07 pytest
Week 13    → 08 mypy & Type Annotations
Week 14–15 → 09 Capstone Project
```

---

## ✅ Progress Tracker

- [ ] 01 Python Internals
- [ ] 02 Concurrency
- [ ] 03 Performance Profiling
- [ ] 04 Packaging
- [ ] 05 FastAPI & Flask
- [ ] 06 SQLAlchemy & Alembic
- [ ] 07 pytest
- [ ] 08 mypy & Type Annotations
- [ ] 09 Capstone — Task Manager API

---

## 🎯 What You Will Build

| Deliverable | Skills Demonstrated |
|-------------|--------------------|
| `cached_property`, descriptor, metaclass implementations | Python internals, data model |
| Concurrent web scraper with rate limiting | asyncio, TaskGroup, Semaphore |
| Flame graph + memory leak diagnosis | py-spy, memray, tracemalloc |
| Published package on TestPyPI | pyproject.toml, uv, wheel |
| **Full Task Manager API** (FastAPI + SQLAlchemy + pytest + mypy) | All pillars combined |

---

## 🧭 Entry Points by Experience Level

| Your background | Start here |
|-----------------|------------|
| New to Python internals | Pillar 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → Capstone |
| Know Python, new to async | Pillar 2 → 5 → 6 → Capstone |
| Know async, need typing/testing | Pillar 7 → 8 → Capstone |
| Interviewing for senior roles | Pillars 1, 2, 5, 6, 7, 8 → Capstone |

---

## 🛠️ Local Dev Setup

```bash
# Prerequisites: Python 3.12+, uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Bootstrap the capstone project (uses all pillars)
uv init task-manager && cd task-manager
uv add fastapi uvicorn sqlalchemy[asyncio] asyncpg alembic pydantic pyjwt argon2-cffi structlog redis
uv add --dev pytest pytest-asyncio pytest-cov pytest-mock httpx mypy ruff factory-boy

# Start local PostgreSQL + Redis
docker run -d --name tm_postgres -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:16
docker run -d --name tm_redis -p 6379:6379 redis:7
```

---

## 🔑 How to Use This Guide

1. **Read** each pillar's `guide.md` top-to-bottom before coding
2. **Code every example** in the guide — don't just read
3. **Complete every exercise** before moving to the next section
4. **Check your understanding** using the self-check questions in each guide
5. **Build the capstone** in `09-capstone/` using everything you learned

---

## 📚 Free Core Resources

| Resource | Covers | Link |
|----------|--------|------|
| Python Official Docs | Internals, data model, stdlib | https://docs.python.org/3/ |
| *Inside the Python Virtual Machine* — Obi Ike-Nwosu | CPython internals, bytecode | https://leanpub.com/insidethepythonvirtualmachine/read |
| *Architecture Patterns with Python* — Percival & Gregory | SQLAlchemy patterns, testing | https://www.cosmicpython.com/ |
| Real Python Tutorials | asyncio, profiling, pytest, typing | https://realpython.com/ |
| Official asyncio docs | asyncio deeply | https://docs.python.org/3/library/asyncio.html |
| pytest Official Docs | pytest completely | https://docs.pytest.org/ |
| mypy Official Docs | mypy, types | https://mypy.readthedocs.io/ |
| Raymond Hettinger talks (YouTube) | Idiomatic Python, internals | https://www.youtube.com/results?search_query=raymond+hettinger+python |
| David Beazley talks (YouTube) | asyncio, concurrency | https://www.youtube.com/results?search_query=david+beazley+python |

> 💡 **Optional paid books** (excellent if you can access them via library/O'Reilly trial):
> *Fluent Python 2nd Ed*, *Python Concurrency with asyncio*, *High Performance Python 2nd Ed*,
> *Python Testing with pytest*, *Robust Python*
