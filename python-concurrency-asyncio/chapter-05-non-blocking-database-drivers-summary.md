# Chapter 5 – Non-Blocking Database Drivers

## Core Idea
Chapter 5 applies the asyncio patterns from Chapter 4 to databases using `asyncpg`, a high-performance async PostgreSQL driver. The key new concepts are **connection pools** (to run many queries concurrently), **asynchronous generators** (for streaming large result sets), and **transaction management** (including nested savepoints).

---

## Why asyncpg?

`psycopg2` (the standard Postgres driver) is synchronous — each query blocks the thread. `asyncpg` is fully async-native and uses a binary protocol for faster data transfer.

```python
import asyncio, asyncpg

async def main():
    conn = await asyncpg.connect(
        host='127.0.0.1', port=5432,
        user='postgres', password='password', database='products'
    )
    # use connection...
    await conn.close()

asyncio.run(main())
```

---

## Defining a Schema and Running Queries

```python
CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS product (
        product_id SERIAL PRIMARY KEY,
        product_name TEXT NOT NULL,
        brand_id INT NOT NULL
    )
"""

async def setup(conn):
    await conn.execute(CREATE_TABLE)

# Parameterised query — prevents SQL injection
products = await conn.fetch(
    'SELECT product_id, product_name FROM product WHERE brand_id = $1',
    brand_id
)
for row in products:
    print(row['product_name'])
```

### Fetch methods

| Method | Returns |
|---|---|
| `conn.fetch(sql, *args)` | List of `Record` objects |
| `conn.fetchrow(sql, *args)` | Single `Record` or `None` |
| `conn.fetchval(sql, *args)` | First column of first row |
| `conn.execute(sql, *args)` | Status string (for INSERT/UPDATE) |

---

## Connection Pools

A single connection handles only one query at a time. To run multiple queries concurrently, you need a **pool** — a fixed set of connections that workers borrow and return.

```python
async def main():
    pool = await asyncpg.create_pool(
        host='127.0.0.1', user='postgres',
        password='password', database='products',
        min_size=6, max_size=6    # 6 connections = 6 concurrent queries
    )

    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO product ...')

    # Or run many queries concurrently with gather:
    async def query(pool, product_id):
        async with pool.acquire() as conn:
            return await conn.fetchrow(
                'SELECT * FROM product WHERE product_id = $1', product_id
            )

    results = await asyncio.gather(*[query(pool, i) for i in range(100)])
    await pool.close()
```

**Pool sizing rule of thumb:** set `min_size = max_size = number_of_cpu_cores × 2` as a starting point; tune from there with load testing.

---

## Asynchronous Generators

Fetching millions of rows at once is memory-heavy. `async for` on a cursor streams rows lazily.

```python
async def main():
    conn = await asyncpg.connect(...)
    async with conn.transaction():
        # asyncpg requires a transaction for server-side cursors
        async for row in conn.cursor('SELECT * FROM large_table'):
            process(row)     # process one row at a time
```

You can also define your own async generator:

```python
async def fetch_products(conn, brand_id):
    async with conn.transaction():
        async for row in conn.cursor(
            'SELECT * FROM product WHERE brand_id = $1', brand_id
        ):
            yield row   # async generator

async def main():
    conn = await asyncpg.connect(...)
    async for product in fetch_products(conn, brand_id=1):
        print(product['product_name'])
```

---

## Transaction Management

### Basic transaction
```python
async with conn.transaction():
    await conn.execute('INSERT INTO product ...')
    await conn.execute('INSERT INTO inventory ...')
# committed on exit; rolled back on exception
```

### Nested transactions (savepoints)
asyncpg automatically uses PostgreSQL savepoints for nested `async with conn.transaction()` blocks:

```python
async with conn.transaction():          # outer — full transaction
    await conn.execute('INSERT ...')
    async with conn.transaction():      # inner — savepoint
        await conn.execute('INSERT ...')
        raise Exception('oops')        # rolls back to savepoint only
    # outer transaction still active — continues
    await conn.execute('INSERT ...')
# outer commits
```

### Manual rollback
```python
transaction = conn.transaction()
await transaction.start()
try:
    await conn.execute('UPDATE ...')
    await transaction.commit()
except Exception:
    await transaction.rollback()
```

---

## Key Takeaway
`asyncpg` + a connection pool lets you run hundreds of concurrent database queries on a single thread. The pattern — `create_pool`, `pool.acquire()` inside tasks, `asyncio.gather` across tasks — maps directly to the web request pattern from Chapter 4. Async generators solve the memory problem for large result sets. Nested transactions isolate partial failures without aborting the outer work.
