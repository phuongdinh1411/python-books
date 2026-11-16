# Chapter 10 – Design Patterns with First-Class Functions

## Core Idea
Several classic Gang-of-Four design patterns become simpler in Python because **functions are first-class objects**. Patterns that exist to pass behaviour as an argument — Strategy, Command, Template Method — can often be replaced by plain functions or callables, eliminating class hierarchies that exist only to wrap a single method.

## The Strategy Pattern Refactored
**Classic Strategy** uses a hierarchy of classes, each implementing a `discount(order)` method:

```python
class Order:
    def __init__(self, cart, customer, promotion=None):
        self.promotion = promotion

    def due(self):
        discount = 0 if self.promotion is None else self.promotion.discount(self)
        return self.total() - discount

class FidelityPromotion:
    def discount(self, order): ...
class BulkPromotion:
    def discount(self, order): ...
```

**Function-Oriented Strategy** replaces the strategy classes with plain functions:

```python
def fidelity_promo(order):
    return order.total() * 0.05 if order.customer.fidelity >= 1000 else 0

def bulk_promo(order):
    discount = sum(item.total() * 0.1 for item in order.cart if item.quantity >= 20)
    return discount

class Order:
    def __init__(self, cart, customer, promotion=None):
        self.promotion = promotion  # just a callable now

    def due(self):
        discount = 0 if self.promotion is None else self.promotion(self)
        return self.total() - discount

Order(cart, joe, fidelity_promo)  # pass the function directly
```

Benefits: no class hierarchy, no instances to create, each strategy is a module-level function directly inspectable and testable.

### Finding All Strategies Automatically
```python
promos = [v for _, v in inspect.getmembers(promotions, inspect.isfunction)]
best_promo = lambda order: max(p(order) for p in promos)
```

### Decorator-Enhanced Strategy
```python
promos = []

def promotion(func):
    promos.append(func)
    return func

@promotion
def fidelity_promo(order): ...

@promotion
def bulk_promo(order): ...
```

## The Command Pattern
Classic Command wraps an action in an object with `.execute()`. With first-class functions:

```python
# Instead of:
class PasteCommand:
    def __init__(self, doc): self.doc = doc
    def execute(self): self.doc.paste()

# Use:
menu.add_item('Paste', lambda: doc.paste())
# Or a callable instance with state:
class MacroCommand:
    def __init__(self, commands):
        self.commands = list(commands)
    def __call__(self):
        for c in self.commands:
            c()
```

## General Principle
> "16 of 23 GoF patterns have qualitatively simpler implementations in dynamic languages." — Peter Norvig

Patterns that exist purely to pass or store behaviour as an object are **artefacts of languages without first-class functions**. In Python, look for patterns where the participant class has a single method with a generic name (`execute`, `run`, `do_it`, `discount`). These are candidates for replacement with plain callables.

## When Class-Based Patterns Still Apply
- When the strategy/command must carry significant mutable state
- When multiple methods are needed (not just one)
- When a richer protocol (cancellation, undo, priority) is required
- When type checking / introspection on the strategy object is important

## Closing Thoughts
This chapter illustrates a broader theme: Python's dynamism makes some OO machinery unnecessary. The right question is not "which pattern fits?" but "what is the simplest representation of this behaviour?" Often a function is simpler than a class. The refactored Strategy and Command examples demonstrate the power of treating functions as values rather than wrapping them in objects.
