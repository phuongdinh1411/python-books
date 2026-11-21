# Pillar 1 — SQL Fundamentals & Advanced SQL

> **Duration:** 2 weeks | **Priority:** 🔴 Critical — foundation for everything

---

## 🎯 Learning Objectives

- Write correct, idiomatic SQL for any CRUD and reporting task
- Master JOINs, GROUP BY, HAVING, subqueries, and CTEs
- Use window functions fluently (ROW_NUMBER, RANK, LAG, LEAD, running totals)
- Write recursive CTEs for hierarchical data
- Understand NULL handling and set operations
- Apply SQL to real analytics tasks (cohorts, funnels, retention)

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [SQLZoo](https://sqlzoo.net/) | 🌐 Interactive | ✅ Free |
| [Mode SQL Tutorial](https://mode.com/sql-tutorial/) | 📄 Tutorial | ✅ Free |
| [pgexercises.com](https://pgexercises.com/) | 🌐 Interactive | ✅ Free |
| [PostgreSQL Tutorial](https://www.postgresqltutorial.com/) | 📄 Tutorial | ✅ Free |
| [Markus Winand — Modern SQL](https://modern-sql.com/) | 🌐 Site | ✅ Free |
| [use-the-index-luke.com](https://use-the-index-luke.com/) | 🌐 Site | ✅ Free (same author as *SQL Performance Explained* book) |
| [W3Schools SQL Reference](https://www.w3schools.com/sql/) | 📄 Reference | ✅ Free |

> 💡 **Optional paid book:** *Learning SQL 3rd Ed* — Alan Beaulieu (O'Reilly)

---

## Setup — Practice Database

```sql
-- Use PostgreSQL for all examples (install via Docker)
-- docker run -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:16

-- Sample schema we'll use throughout
CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    full_name   VARCHAR(255),
    country     VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    category    VARCHAR(100),
    price       NUMERIC(10, 2),
    cost        NUMERIC(10, 2),
    stock       INTEGER DEFAULT 0
);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    status      VARCHAR(50) DEFAULT 'pending',
    total       NUMERIC(10, 2),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER REFERENCES orders(id),
    product_id  INTEGER REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    unit_price  NUMERIC(10, 2) NOT NULL
);

CREATE TABLE events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER,
    event_type  VARCHAR(100),
    page        VARCHAR(255),
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Section 1 — SELECT Foundations

### SELECT, WHERE, ORDER BY, LIMIT

```sql
-- Basic select
SELECT id, full_name, email FROM customers;

-- All columns (avoid in production — always name columns)
SELECT * FROM customers;

-- Filtering
SELECT * FROM orders
WHERE status = 'completed'
  AND total > 100
  AND created_at >= '2024-01-01';

-- Pattern matching
SELECT * FROM customers
WHERE email LIKE '%@gmail.com'   -- % = any chars
  OR full_name ILIKE 'alice%';   -- ILIKE = case-insensitive

-- IN and BETWEEN
SELECT * FROM products
WHERE category IN ('Electronics', 'Clothing')
  AND price BETWEEN 10 AND 500;

-- Sorting
SELECT * FROM products
ORDER BY price DESC, name ASC;

-- Pagination
SELECT * FROM products
ORDER BY id
LIMIT 20 OFFSET 40;   -- page 3 (0-indexed)
```

### NULL Handling — The Most Common Trap

```sql
-- NULL is NOT a value — it's the absence of a value
-- NULL = NULL is UNKNOWN (not TRUE!)

SELECT * FROM customers WHERE full_name = NULL;    -- WRONG: returns nothing
SELECT * FROM customers WHERE full_name IS NULL;   -- CORRECT
SELECT * FROM customers WHERE full_name IS NOT NULL;

-- COALESCE: return first non-null value
SELECT
    id,
    COALESCE(full_name, 'Anonymous') AS display_name,
    COALESCE(country, 'Unknown') AS country
FROM customers;

-- NULLIF: return NULL if two values are equal
SELECT NULLIF(stock, 0) AS stock  -- NULL when stock=0 (avoids divide-by-zero)
FROM products;

-- NULLs in aggregates: COUNT(*) counts rows, COUNT(col) skips NULLs
SELECT
    COUNT(*)           AS total_rows,
    COUNT(full_name)   AS rows_with_name,
    COUNT(DISTINCT country) AS unique_countries
FROM customers;
```

---

## Section 2 — JOINs

```
         INNER JOIN          LEFT JOIN           RIGHT JOIN         FULL JOIN
       ┌────┬────┐         ┌────┬────┐         ┌────┬────┐       ┌────┬────┐
  A    │ A∩B│    │ B   A   │ A  │A∩B │ B   A   │    │A∩B │ B  A  │ A  │A∩B │ B
  ─────┼────┼────┤    ─────┼────┼────┤    ─────┼────┼────┤  ─────┼────┼────┤
       │only│    │         │only│    │         │    │only│        │only│only│
       └────┴────┘         └────┴────┘         └────┴────┘       └────┴────┘
     both sides only        all of A            all of B           both sides
```

```sql
-- INNER JOIN: only matching rows from both sides
SELECT
    o.id AS order_id,
    c.full_name,
    o.total,
    o.status
FROM orders o
INNER JOIN customers c ON o.customer_id = c.id;

-- LEFT JOIN: all orders, customer info if it exists
SELECT
    o.id,
    c.full_name,  -- NULL if no customer match
    o.total
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id;

-- Find orders with NO customer (data quality check)
SELECT o.*
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE c.id IS NULL;

-- Multiple JOINs
SELECT
    o.id AS order_id,
    c.full_name AS customer,
    p.name AS product,
    oi.quantity,
    oi.unit_price,
    (oi.quantity * oi.unit_price) AS line_total
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'completed'
ORDER BY o.created_at DESC;

-- SELF JOIN: compare rows in same table
SELECT
    a.full_name AS customer,
    b.full_name AS referred_by
FROM customers a
LEFT JOIN customers b ON a.referred_by_id = b.id;

-- CROSS JOIN: cartesian product (every combination)
SELECT p1.name, p2.name
FROM products p1
CROSS JOIN products p2
WHERE p1.id < p2.id;   -- avoid duplicates
```

---

## Section 3 — Aggregation

```sql
-- Basic aggregates
SELECT
    COUNT(*)                    AS total_orders,
    SUM(total)                  AS revenue,
    AVG(total)                  AS avg_order_value,
    MIN(total)                  AS min_order,
    MAX(total)                  AS max_order,
    PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY total) AS median_order
FROM orders
WHERE status = 'completed';

-- GROUP BY
SELECT
    c.country,
    COUNT(o.id)      AS order_count,
    SUM(o.total)     AS total_revenue,
    AVG(o.total)     AS avg_order
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.status = 'completed'
GROUP BY c.country
ORDER BY total_revenue DESC;

-- HAVING: filter on aggregated results (WHERE can't do this)
SELECT
    customer_id,
    COUNT(*) AS order_count,
    SUM(total) AS lifetime_value
FROM orders
WHERE status = 'completed'
GROUP BY customer_id
HAVING COUNT(*) >= 5           -- only customers with 5+ orders
   AND SUM(total) > 1000
ORDER BY lifetime_value DESC;

-- ROLLUP: add subtotals and grand total
SELECT
    COALESCE(country, 'ALL') AS country,
    COALESCE(status, 'ALL')  AS status,
    COUNT(*)                  AS orders,
    SUM(total)                AS revenue
FROM orders o
JOIN customers c ON o.customer_id = c.id
GROUP BY ROLLUP (country, status);

-- CUBE: all combinations of subtotals
GROUP BY CUBE (country, status, DATE_TRUNC('month', o.created_at));
```

---

## Section 4 — Subqueries and CTEs

### Subqueries

```sql
-- Scalar subquery (returns one value)
SELECT *
FROM orders
WHERE total > (
    SELECT AVG(total) FROM orders WHERE status = 'completed'
);

-- IN subquery
SELECT * FROM customers
WHERE id IN (
    SELECT DISTINCT customer_id
    FROM orders
    WHERE total > 500
);

-- EXISTS (more efficient than IN for large sets)
SELECT * FROM customers c
WHERE EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = c.id
      AND o.status = 'completed'
      AND o.total > 500
);

-- Correlated subquery (references outer query — runs once per row)
SELECT
    p.name,
    p.price,
    (SELECT AVG(oi.unit_price)
     FROM order_items oi
     WHERE oi.product_id = p.id) AS avg_sold_price
FROM products p;
```

### CTEs (Common Table Expressions)

CTEs make complex queries readable by naming intermediate results.

```sql
-- Basic CTE
WITH completed_orders AS (
    SELECT *
    FROM orders
    WHERE status = 'completed'
),
high_value_customers AS (
    SELECT customer_id, SUM(total) AS lifetime_value
    FROM completed_orders
    GROUP BY customer_id
    HAVING SUM(total) > 1000
)
SELECT
    c.full_name,
    c.email,
    hvc.lifetime_value
FROM customers c
JOIN high_value_customers hvc ON c.id = hvc.customer_id
ORDER BY hvc.lifetime_value DESC;


-- Multiple CTEs chained
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', created_at) AS month,
        SUM(total) AS revenue
    FROM orders
    WHERE status = 'completed'
    GROUP BY 1
),
revenue_with_lag AS (
    SELECT
        month,
        revenue,
        LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue
    FROM monthly_revenue
)
SELECT
    month,
    revenue,
    prev_month_revenue,
    ROUND(
        (revenue - prev_month_revenue) / prev_month_revenue * 100, 2
    ) AS mom_growth_pct
FROM revenue_with_lag
ORDER BY month;
```

### Recursive CTEs — Hierarchical Data

```sql
-- Employee hierarchy (manager → reports)
CREATE TABLE employees (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100),
    manager_id  INTEGER REFERENCES employees(id)
);

WITH RECURSIVE org_chart AS (
    -- Base case: top-level (CEO, no manager)
    SELECT id, name, manager_id, 0 AS depth, name::text AS path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive case: join children to their parent
    SELECT
        e.id,
        e.name,
        e.manager_id,
        oc.depth + 1,
        oc.path || ' > ' || e.name
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.id
)
SELECT
    REPEAT('  ', depth) || name AS org_tree,
    depth,
    path
FROM org_chart
ORDER BY path;
```

---

## Section 5 — Window Functions (Most Powerful SQL Feature)

Window functions compute across a "window" of related rows **without collapsing them**.

```sql
-- Syntax:
-- function() OVER (PARTITION BY col ORDER BY col ROWS/RANGE frame)

-- ROW_NUMBER: sequential rank, no ties
SELECT
    id,
    full_name,
    country,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY country ORDER BY created_at) AS sign_up_rank
FROM customers;

-- RANK vs DENSE_RANK
SELECT
    id,
    total,
    RANK()       OVER (ORDER BY total DESC) AS rank,       -- gaps on ties: 1,2,2,4
    DENSE_RANK() OVER (ORDER BY total DESC) AS dense_rank, -- no gaps: 1,2,2,3
    ROW_NUMBER() OVER (ORDER BY total DESC) AS row_num     -- always unique: 1,2,3,4
FROM orders;

-- LAG and LEAD: access previous/next rows
SELECT
    id,
    customer_id,
    total,
    created_at,
    LAG(total)  OVER (PARTITION BY customer_id ORDER BY created_at) AS prev_order_total,
    LEAD(total) OVER (PARTITION BY customer_id ORDER BY created_at) AS next_order_total,
    total - LAG(total) OVER (PARTITION BY customer_id ORDER BY created_at) AS change_from_prev
FROM orders
ORDER BY customer_id, created_at;

-- Running total and moving average
SELECT
    created_at::date AS date,
    SUM(total) AS daily_revenue,
    SUM(SUM(total)) OVER (ORDER BY created_at::date) AS running_total,
    AVG(SUM(total)) OVER (
        ORDER BY created_at::date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW   -- 7-day moving average
    ) AS moving_avg_7d
FROM orders
WHERE status = 'completed'
GROUP BY created_at::date
ORDER BY date;

-- FIRST_VALUE / LAST_VALUE
SELECT
    customer_id,
    id AS order_id,
    total,
    created_at,
    FIRST_VALUE(total) OVER (
        PARTITION BY customer_id ORDER BY created_at
    ) AS first_order_total,
    LAST_VALUE(total) OVER (
        PARTITION BY customer_id ORDER BY created_at
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_order_total
FROM orders;

-- NTILE: split into N buckets
SELECT
    customer_id,
    SUM(total) AS lifetime_value,
    NTILE(4) OVER (ORDER BY SUM(total)) AS quartile
FROM orders
GROUP BY customer_id;
-- quartile 4 = top 25% by LTV
```

---

## Section 6 — Analytics SQL Patterns

### Cohort Analysis

```sql
-- Monthly cohort: when did each customer first purchase?
WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', MIN(created_at)) AS cohort_month
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
customer_orders AS (
    SELECT
        o.customer_id,
        c.cohort_month,
        DATE_TRUNC('month', o.created_at) AS order_month,
        EXTRACT(YEAR FROM AGE(
            DATE_TRUNC('month', o.created_at),
            c.cohort_month
        )) * 12 +
        EXTRACT(MONTH FROM AGE(
            DATE_TRUNC('month', o.created_at),
            c.cohort_month
        )) AS months_since_first
    FROM orders o
    JOIN cohorts c ON o.customer_id = c.customer_id
    WHERE o.status = 'completed'
)
SELECT
    cohort_month,
    months_since_first,
    COUNT(DISTINCT customer_id) AS active_customers
FROM customer_orders
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Funnel Analysis

```sql
-- Conversion funnel: view → add_to_cart → checkout → purchase
WITH funnel AS (
    SELECT
        user_id,
        MAX(CASE WHEN event_type = 'page_view'    THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN event_type = 'add_to_cart'  THEN 1 ELSE 0 END) AS added,
        MAX(CASE WHEN event_type = 'checkout'     THEN 1 ELSE 0 END) AS checked_out,
        MAX(CASE WHEN event_type = 'purchase'     THEN 1 ELSE 0 END) AS purchased
    FROM events
    WHERE occurred_at >= NOW() - INTERVAL '30 days'
    GROUP BY user_id
)
SELECT
    SUM(viewed)      AS step1_views,
    SUM(added)       AS step2_add_to_cart,
    SUM(checked_out) AS step3_checkout,
    SUM(purchased)   AS step4_purchase,
    ROUND(SUM(added)::numeric       / NULLIF(SUM(viewed), 0) * 100, 2) AS view_to_cart_pct,
    ROUND(SUM(checked_out)::numeric / NULLIF(SUM(added), 0) * 100, 2) AS cart_to_checkout_pct,
    ROUND(SUM(purchased)::numeric   / NULLIF(SUM(checked_out), 0) * 100, 2) AS checkout_to_purchase_pct
FROM funnel;
```

### Retention Analysis (N-Day Retention)

```sql
-- Day-N retention: % of users who return N days after signup
WITH user_days AS (
    SELECT
        user_id,
        MIN(occurred_at::date) AS first_day,
        (occurred_at::date - MIN(occurred_at::date) OVER (PARTITION BY user_id)) AS day_number
    FROM events
    GROUP BY user_id, occurred_at::date
)
SELECT
    day_number,
    COUNT(DISTINCT user_id)                               AS retained_users,
    COUNT(DISTINCT user_id) FILTER (WHERE day_number = 0) AS cohort_size,
    ROUND(
        COUNT(DISTINCT user_id)::numeric /
        COUNT(DISTINCT user_id) FILTER (WHERE day_number = 0) * 100, 2
    ) AS retention_pct
FROM user_days
WHERE day_number BETWEEN 0 AND 30
GROUP BY day_number
ORDER BY day_number;
```

---

## Section 7 — Date/Time Operations

```sql
-- Extract parts
SELECT
    created_at,
    EXTRACT(YEAR  FROM created_at) AS year,
    EXTRACT(MONTH FROM created_at) AS month,
    EXTRACT(DOW   FROM created_at) AS day_of_week,  -- 0=Sunday
    EXTRACT(HOUR  FROM created_at) AS hour
FROM orders;

-- Truncate
SELECT
    DATE_TRUNC('day',   created_at) AS day,
    DATE_TRUNC('week',  created_at) AS week,
    DATE_TRUNC('month', created_at) AS month,
    DATE_TRUNC('year',  created_at) AS year
FROM orders;

-- Intervals and arithmetic
SELECT
    NOW() AS now,
    NOW() - INTERVAL '7 days' AS one_week_ago,
    NOW() + INTERVAL '1 month' AS next_month,
    created_at + INTERVAL '30 days' AS expires_at
FROM orders;

-- Age and duration
SELECT
    customer_id,
    MIN(created_at) AS first_order,
    MAX(created_at) AS last_order,
    AGE(MAX(created_at), MIN(created_at)) AS customer_tenure,
    EXTRACT(DAYS FROM AGE(MAX(created_at), MIN(created_at))) AS tenure_days
FROM orders
GROUP BY customer_id;

-- Time zones
SELECT
    created_at                              AS utc,
    created_at AT TIME ZONE 'UTC'           AS utc_explicit,
    created_at AT TIME ZONE 'America/New_York' AS eastern,
    created_at AT TIME ZONE 'Asia/Tokyo'    AS tokyo
FROM orders;
```

---

## Section 8 — Set Operations

```sql
-- UNION: combine result sets, removes duplicates
SELECT email FROM customers
UNION
SELECT email FROM newsletter_subscribers;

-- UNION ALL: combine without deduplication (faster)
SELECT 'customers' AS source, email FROM customers
UNION ALL
SELECT 'subscribers', email FROM newsletter_subscribers;

-- INTERSECT: rows in BOTH results
SELECT customer_id FROM orders WHERE status = 'completed'
INTERSECT
SELECT customer_id FROM orders WHERE total > 1000;

-- EXCEPT: rows in first but NOT second (find churned users)
SELECT id FROM customers
EXCEPT
SELECT DISTINCT customer_id FROM orders WHERE created_at > NOW() - INTERVAL '90 days';
```

---

## 🏋️ Exercises

### Exercise 1 — Sales Report
Write a query that returns the top 10 products by revenue in the last 90 days,
including: product name, units sold, total revenue, % of total revenue.

### Exercise 2 — Customer Segmentation (RFM)
Segment customers by **Recency** (days since last order), **Frequency** (order count),
and **Monetary** (total spend). Use NTILE(5) for each dimension.

### Exercise 3 — Month-over-Month Growth
Using window functions, compute: monthly revenue, previous month revenue, MoM growth %,
and 3-month rolling average. Flag months where growth was negative.

### Exercise 4 — Identify Gaps
Find all customers who made at least 2 orders with a gap of more than 60 days
between consecutive orders.

---

## ✅ Self-Check Questions

1. What is the difference between WHERE and HAVING?
2. When should you use EXISTS instead of IN?
3. What is the difference between RANK, DENSE_RANK, and ROW_NUMBER?
4. What does PARTITION BY do in a window function?
5. Why is `COUNT(col)` different from `COUNT(*)`?
6. What does a recursive CTE need to work correctly?
7. When would you use UNION ALL instead of UNION?
8. What is the ROWS BETWEEN clause in a window function?
9. What is a correlated subquery and when is it slow?
10. What does COALESCE do?

---

## 🔗 Key Links

- https://sqlzoo.net/
- https://pgexercises.com/
- https://mode.com/sql-tutorial/advanced-sql/
- https://modern-sql.com/
- https://www.postgresql.org/docs/current/functions-window.html
