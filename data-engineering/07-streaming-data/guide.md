# Pillar 7 — Streaming Data (Kafka & Stream Processing)

> **Duration:** 2 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

- Understand Kafka's core concepts: topics, partitions, offsets, consumer groups
- Produce and consume messages with the Python `confluent-kafka` client
- Implement exactly-once semantics and handle consumer failures
- Use Spark Structured Streaming for stateful stream processing
- Design streaming pipeline patterns: enrichment, deduplication, windowed aggregations
- Monitor Kafka: consumer lag, throughput, partition leadership

---

## 📚 Resources

| Resource | Type | Priority |
|----------|------|----------|
| *Kafka: The Definitive Guide 2nd Ed* — Shapira et al. | 📖 Book | Must |
| [Kafka Official Docs](https://kafka.apache.org/documentation/) | 📄 Docs | Must |
| [Confluent Developer](https://developer.confluent.io/) | 🌐 Site | Must — free courses |
| [Faust (Python Streaming)](https://faust-streaming.github.io/faust/) | 📄 Docs | Recommended |

---

## Section 1 — Kafka Architecture

```
                        KAFKA CLUSTER
        ┌─────────────────────────────────────────┐
        │                                          │
        │   Broker 1        Broker 2    Broker 3  │
        │   ┌─────────┐    ┌─────────┐  ┌───────┐ │
        │   │Topic A  │    │Topic A  │  │Topic A│ │
        │   │Part 0 L │    │Part 1 L │  │Part 2L│ │
        │   │Part 1 F │    │Part 2 F │  │Part 0F│ │
        │   └─────────┘    └─────────┘  └───────┘ │
        └─────────────────────────────────────────┘
              ↑                           ↓
        Producer                    Consumer Group A
                                    ├── Consumer 1 → Partition 0, 1
                                    └── Consumer 2 → Partition 2

L = Leader (handles reads/writes)
F = Follower (replica for fault tolerance)
```

### Core Concepts

```
Topic        → named stream of records (like a database table)
Partition    → ordered, immutable log within a topic
Offset       → position of a record within a partition (monotonically increasing)
Consumer Group → group of consumers sharing partitions (each partition → 1 consumer)
Replication  → partition replicated to N brokers for fault tolerance
Retention    → how long Kafka keeps messages (time-based or size-based)

Key properties:
- Messages are immutable once written
- Consumers track their own offset (Kafka doesn't delete on consume)
- Multiple consumer groups can read the same topic independently
- Max parallelism = number of partitions (each consumer reads ≤ 1 partition)
```

---

## Section 2 — Python Kafka Client

```bash
pip install confluent-kafka
```

### Producer

```python
# producers/order_producer.py
import json
import logging
from confluent_kafka import Producer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

KAFKA_CONFIG = {
    "bootstrap.servers": "localhost:9092",
    "acks": "all",                   # wait for all replicas to acknowledge
    "enable.idempotence": True,       # exactly-once producer semantics
    "retries": 10,
    "max.in.flight.requests.per.connection": 5,
    "compression.type": "snappy",
    "batch.size": 32768,             # 32KB batch size
    "linger.ms": 10,                 # wait up to 10ms to batch messages
}


def delivery_callback(err, msg):
    """Called when a message is delivered or fails."""
    if err:
        logger.error(f"Delivery failed for {msg.key()}: {err}")
    else:
        logger.debug(f"Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")


class OrderProducer:
    def __init__(self, config: dict = KAFKA_CONFIG):
        self.producer = Producer(config)
        self.topic = "orders"

    def send_order(self, order: dict) -> None:
        """Send an order event to Kafka."""
        key = str(order["customer_id"]).encode()   # partition by customer_id
        value = json.dumps({
            **order,
            "event_type": "order_created",
            "event_time": datetime.utcnow().isoformat(),
        }).encode()

        try:
            self.producer.produce(
                topic=self.topic,
                key=key,
                value=value,
                callback=delivery_callback,
            )
            # Poll to trigger delivery callbacks (non-blocking)
            self.producer.poll(0)
        except KafkaException as e:
            logger.error(f"Failed to produce message: {e}")
            raise

    def flush(self, timeout: float = 10.0) -> None:
        """Wait for all messages to be delivered."""
        remaining = self.producer.flush(timeout)
        if remaining > 0:
            logger.warning(f"{remaining} messages still in queue after flush!")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.flush()


# Usage:
with OrderProducer() as producer:
    for order in get_orders():
        producer.send_order(order)
```

### Consumer

```python
# consumers/order_consumer.py
import json
import logging
import signal
from confluent_kafka import Consumer, KafkaException, KafkaError
from typing import Callable

logger = logging.getLogger(__name__)

CONSUMER_CONFIG = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "order-processor",
    "auto.offset.reset": "earliest",   # start from beginning if no offset
    "enable.auto.commit": False,        # manual commit for exactly-once
    "max.poll.interval.ms": 300000,     # 5 min max processing time per poll
    "session.timeout.ms": 30000,
    "heartbeat.interval.ms": 10000,
}


class OrderConsumer:
    def __init__(self, topics: list[str], config: dict = CONSUMER_CONFIG):
        self.consumer = Consumer(config)
        self.consumer.subscribe(
            topics,
            on_assign=self._on_assign,
            on_revoke=self._on_revoke,
        )
        self.running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _on_assign(self, consumer, partitions):
        logger.info(f"Assigned partitions: {[p.partition for p in partitions]}")

    def _on_revoke(self, consumer, partitions):
        logger.info(f"Revoked partitions: {[p.partition for p in partitions]}")
        # Commit offsets before rebalance (important for at-least-once)
        consumer.commit(asynchronous=False)

    def _shutdown(self, signum, frame):
        logger.info("Shutdown signal received")
        self.running = False

    def consume(self, process_fn: Callable[[dict], None], batch_size: int = 100) -> None:
        """Consume and process messages in batches."""
        try:
            while self.running:
                messages = self.consumer.consume(num_messages=batch_size, timeout=1.0)

                if not messages:
                    continue

                batch = []
                for msg in messages:
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            continue   # end of partition (normal)
                        raise KafkaException(msg.error())

                    try:
                        record = json.loads(msg.value().decode("utf-8"))
                        batch.append(record)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON at offset {msg.offset()}: {e}")
                        continue

                if batch:
                    try:
                        process_fn(batch)
                        # Commit AFTER processing — at-least-once delivery
                        self.consumer.commit(asynchronous=False)
                        logger.info(f"Processed and committed batch of {len(batch)}")
                    except Exception as e:
                        logger.error(f"Failed to process batch: {e}")
                        # Don't commit — messages will be redelivered after rebalance
                        raise

        finally:
            self.consumer.close()


# Usage:
def save_to_db(orders: list[dict]) -> None:
    with db_session() as session:
        for order in orders:
            session.execute("""
                INSERT INTO orders (id, customer_id, total, created_at)
                VALUES (:id, :customer_id, :total, :created_at)
                ON CONFLICT (id) DO NOTHING
            """, order)

consumer = OrderConsumer(["orders"])
consumer.consume(save_to_db)
```

### Consumer Lag Monitoring

```python
from confluent_kafka import Consumer, TopicPartition

def get_consumer_lag(group_id: str, topics: list[str]) -> dict:
    """Check how far behind a consumer group is."""
    consumer = Consumer({
        "bootstrap.servers": "localhost:9092",
        "group.id": group_id,
    })

    lag_report = {}
    for topic in topics:
        metadata = consumer.list_topics(topic)
        partitions = [
            TopicPartition(topic, p)
            for p in metadata.topics[topic].partitions
        ]
        # Get committed offsets (where consumer is)
        committed = consumer.committed(partitions)
        # Get end offsets (where producer is)
        end_offsets = consumer.get_watermark_offsets

        for partition in partitions:
            tp = TopicPartition(partition.topic, partition.partition)
            low, high = consumer.get_watermark_offsets(tp)
            committed_offset = committed[partitions.index(partition)].offset
            lag = high - committed_offset if committed_offset >= 0 else high
            lag_report[f"{topic}[{partition.partition}]"] = lag

    consumer.close()
    return lag_report
```

---

## Section 3 — Delivery Semantics

```
At-most-once   → produce: no retry; consume: commit before processing
                 Risk: data loss. Use when: metrics, logs (OK to lose some)

At-least-once  → produce: retry on failure; consume: commit after processing
                 Risk: duplicates. Use when: most real-world cases
                 Fix duplicates with: idempotent consumer (upsert, dedup key)

Exactly-once   → Kafka Transactions (expensive, complex)
                 Use when: financial data, counters that must be precise
```

```python
# Idempotent consumer pattern (at-least-once + dedup = effectively exactly-once)
def upsert_orders(orders: list[dict]) -> None:
    with db_session() as session:
        for order in orders:
            session.execute("""
                INSERT INTO orders (id, customer_id, total, kafka_offset)
                VALUES (:id, :customer_id, :total, :kafka_offset)
                ON CONFLICT (id) DO UPDATE
                    SET total        = EXCLUDED.total,
                        kafka_offset = EXCLUDED.kafka_offset
                -- Idempotent: same message processed twice = same result
            """, {**order, "kafka_offset": order["_offset"]})
```

---

## Section 4 — Spark Structured Streaming

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StringType, DoubleType, TimestampType

spark = SparkSession.builder \
    .appName("Order Stream Processor") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .getOrCreate()

# Define schema for JSON messages
order_schema = StructType() \
    .add("id", "integer") \
    .add("customer_id", "integer") \
    .add("total", DoubleType()) \
    .add("status", StringType()) \
    .add("event_time", TimestampType())

# Read from Kafka (streaming source)
raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "orders") \
    .option("startingOffsets", "latest") \
    .option("maxOffsetsPerTrigger", 100_000) \
    .load()

# Parse JSON
orders = raw_stream.select(
    F.col("key").cast("string").alias("kafka_key"),
    F.col("offset").alias("kafka_offset"),
    F.col("timestamp").alias("kafka_timestamp"),
    F.from_json(F.col("value").cast("string"), order_schema).alias("data")
).select("kafka_offset", "data.*")

# Filter and clean
valid_orders = orders.filter(
    F.col("id").isNotNull() &
    (F.col("total") > 0) &
    (F.col("status").isin("completed", "pending"))
)
```

### Windowed Aggregations

```python
# Tumbling window (non-overlapping)
windowed = valid_orders \
    .withWatermark("event_time", "10 minutes") \
    .groupBy(
        F.window(F.col("event_time"), "5 minutes"),  # 5-minute windows
        F.col("status")
    ).agg(
        F.count("id").alias("order_count"),
        F.sum("total").alias("revenue"),
    )

# Sliding window (overlapping)
sliding = valid_orders \
    .withWatermark("event_time", "30 minutes") \
    .groupBy(
        F.window(F.col("event_time"), "15 minutes", "5 minutes"),  # 15-min window, 5-min slide
        F.col("status")
    ).agg(F.count("id").alias("orders"))
```

### Writing Streaming Output

```python
# Write to Kafka (output topic)
query_kafka = windowed \
    .select(
        F.col("window.start").cast("string").alias("key"),
        F.to_json(F.struct("*")).alias("value")
    ).writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("topic", "order_aggregates") \
    .option("checkpointLocation", "/tmp/checkpoints/order_agg") \
    .outputMode("update") \
    .trigger(processingTime="30 seconds") \
    .start()

# Write to PostgreSQL
def write_to_postgres(batch_df, batch_id):
    batch_df.write \
        .jdbc(
            url="jdbc:postgresql://host:5432/analytics",
            table="order_aggregates",
            mode="append",
            properties={"user": "user", "password": "pass"},
        )

query_pg = windowed.writeStream \
    .foreachBatch(write_to_postgres) \
    .option("checkpointLocation", "/tmp/checkpoints/order_pg") \
    .outputMode("update") \
    .start()

# Await termination
query_kafka.awaitTermination()
```

---

## Section 5 — Streaming Pipeline Patterns

### Pattern 1: Stream Enrichment

```python
# Enrich streaming orders with customer data from a static DataFrame
customers = spark.read.parquet("customers/")  # static data
customers.cache()

enriched = valid_orders.join(
    broadcast(customers),
    on="customer_id",
    how="left"
)
```

### Pattern 2: Deduplication

```python
# Deduplicate within a watermark window
deduplicated = valid_orders \
    .withWatermark("event_time", "1 hour") \
    .dropDuplicates(["id", "event_time"])  # dedup by order_id within window
```

### Pattern 3: Late Data Handling

```python
# Watermark: how late data can arrive before it's dropped
# "10 minutes" = accept events up to 10 minutes late
orders_with_watermark = orders \
    .withWatermark("event_time", "10 minutes") \
    .groupBy(
        F.window("event_time", "5 minutes")
    ).count()
# State is kept until: window end + watermark delay = safe to output
```

---

## 🏋️ Exercises

### Exercise 1 — Producer + Consumer
Build an order event system:
- Producer: generate 10,000 fake orders and send to Kafka
- Consumer: read and upsert into PostgreSQL
- Handle: bad JSON, delivery failures, consumer rebalance

### Exercise 2 — Spark Streaming Aggregation
Build a streaming job that:
- Reads from `orders` Kafka topic
- Computes 5-minute windowed revenue by country
- Writes results to a `order_metrics` Postgres table
- Handles late data (10-minute watermark)

### Exercise 3 — Consumer Lag Dashboard
Write a script that polls consumer lag every 30 seconds and alerts (print/log)
if any partition's lag exceeds 10,000 messages.

---

## ✅ Self-Check Questions

1. What is a Kafka partition and what determines max parallelism?
2. What is a consumer group?
3. What is the difference between at-least-once and exactly-once delivery?
4. What is consumer lag and why does it matter?
5. What is a watermark in Spark Structured Streaming?
6. What is the difference between a tumbling and sliding window?
7. Why should you set `enable.auto.commit = false`?
8. What is a checkpoint in Spark Streaming?
9. What does `outputMode("update")` vs `"append"` vs `"complete"` mean?
10. What is a rebalance and what triggers it?

---

## 🔗 Key Links

- https://kafka.apache.org/documentation/
- https://developer.confluent.io/courses/
- https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- https://docs.confluent.io/kafka-clients/python/current/overview.html
