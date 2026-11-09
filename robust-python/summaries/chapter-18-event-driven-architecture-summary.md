# Chapter 18 – Event-Driven Architecture

## Core Idea
**Event-driven architecture (EDA)** decouples producers of information from consumers of that information. Instead of direct function calls, components communicate through events — making systems more extensible, observable, and independently deployable.

## How It Works
- A **producer** emits an event when something happens ("ingredient restocked", "order placed")
- A **consumer** reacts to events it cares about, independently of the producer
- The producer doesn't know or care who (if anyone) is listening

```
Producer → Event → [Broker/Bus] → Consumer A
                                 → Consumer B
                                 → Consumer C
```

### Drawbacks
- Harder to trace execution flow (no direct call stack)
- Debugging across async event boundaries is more complex
- Ordering and delivery guarantees require careful design
- Not suitable for everything — synchronous request/response patterns are often simpler

## Simple Events

### Using a Message Broker (in-process)
```python
class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def publish(self, event: str, data: Any) -> None:
        for handler in self._handlers.get(event, []):
            handler(data)

bus = EventBus()
bus.subscribe("order_placed", send_confirmation_email)
bus.subscribe("order_placed", update_inventory)
bus.publish("order_placed", order_data)
```
- Producers and consumers are **decoupled** — neither references the other
- New consumers added by subscribing, no existing code changes (OCP)

### The Observer Pattern
A classic GoF pattern for event-driven behavior:
```python
class Subject:
    def __init__(self):
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)

    def notify(self, event: str) -> None:
        for obs in self._observers:
            obs.update(event)
```
- Subject (producer) maintains a list of observers (consumers)
- Consumers implement an `update()` interface
- More structured than a bare message broker; preferred when the observer relationship is a first-class concept

## Streaming Events
For high-volume, ordered, or replayable event streams:
- Tools: **Apache Kafka**, **Redis Streams**, **AWS Kinesis**
- Producers append events to a log; consumers read from an offset
- Consumers can replay history, catch up after downtime, and process in parallel
- Python: `kafka-python`, `aiokafka` for Kafka; `redis-py` streams API

Use streaming events when:
- Events must be persistent and replayable
- Multiple independent consumers need to process the same events
- High throughput is required
- You need ordering guarantees across distributed consumers

## When to Use Event-Driven Architecture
✅ Decoupling components that change independently  
✅ Fan-out (one event, many reactions)  
✅ Audit logs and observability  
✅ Asynchronous workflows (email sending, notifications)  
✅ Integrating systems that shouldn't know about each other  

❌ Simple request/response flows  
❌ When you need tight transactional consistency  
❌ When the call graph needs to be easy to trace synchronously  

## Closing Thoughts
Event-driven architecture is a powerful extensibility tool at the architectural level. When you decouple via events, adding new behaviors means adding new consumers — no existing code changes. This is the Open-Closed Principle applied at the system design level.
