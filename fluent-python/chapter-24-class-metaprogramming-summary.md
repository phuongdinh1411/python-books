# Chapter 24 – Class Metaprogramming

## Core Idea
Python provides multiple tools for **creating or customising classes at runtime**: class factory functions, `type()`, `__init_subclass__`, class decorators, and metaclasses. Each successive tool is more powerful but also more complex — use the simplest one that solves the problem.

## Classes as Objects
Every class is an instance of `type`. Classes have attributes (`__name__`, `__bases__`, `__dict__`, `__mro__`) and can be inspected and modified at runtime.

```python
MyClass.__bases__      # (BaseClass,)
MyClass.__mro__        # (MyClass, BaseClass, object)
MyClass.__dict__       # class namespace
```

## `type`: The Built-In Class Factory
```python
# type(name, bases, dict) creates a new class
MyClass = type('MyClass', (Base,), {'x': 42, 'hello': lambda self: 'Hello'})
```
This is equivalent to:
```python
class MyClass(Base):
    x = 42
    def hello(self): return 'Hello'
```

## Class Factory Functions
Use when many similar classes need to be generated programmatically:
```python
def record_factory(cls_name, field_names):
    field_names = field_names.replace(',', ' ').split()
    cls_attrs = {}
    def __init__(self, *args, **kwargs):
        ...
    cls_attrs['__init__'] = __init__
    return type(cls_name, (object,), cls_attrs)

Dog = record_factory('Dog', 'name weight')
```

## `__init_subclass__`
Runs in the **superclass** whenever a subclass is created — a lightweight hook to validate or register subclasses without metaclasses:
```python
class Checked:
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, val in cls.__dict__.items():
            if isinstance(val, Field):
                val.__set_name__(cls, name)   # register all Field descriptors
```

## Class Decorators
Apply arbitrary transformations to a class after it is created:
```python
def validate_fields(cls):
    for name, val in cls.__dict__.items():
        if isinstance(val, Field):
            val.__set_name__(cls, name)
    return cls

@validate_fields
class Movie:
    title = NonBlank()
    year = Validated()
```
Class decorators are simpler than metaclasses for most customisation needs.

## Import Time vs Runtime
```python
# A class body executes at import time (during class definition)
# A function body executes at call time

class C:
    print('class body runs at import time')

    def method(self):
        print('method body runs at call time')
```
Understanding this ordering is critical when debugging decorators, metaclasses, and descriptor `__set_name__` calls.

## Metaclasses
A metaclass is a class whose instances are classes. `type` is the default metaclass:
```python
class Meta(type):
    def __new__(mcs, name, bases, namespace):
        print(f'Creating class {name}')
        cls = super().__new__(mcs, name, bases, namespace)
        return cls

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)

class MyClass(metaclass=Meta):
    pass
```

### Metaclass `__prepare__`
Returns the mapping used as the class namespace — enables ordered or custom namespaces before the class body executes:
```python
class OrderedMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return collections.OrderedDict()
```

## When to Use Each Tool

| Tool | Use when |
|---|---|
| Class factory (`type()`) | Generate a series of similar classes at runtime |
| `__init_subclass__` | Validate or configure subclasses; register plugin classes |
| Class decorator | Transform a single class at definition time |
| Metaclass | Customise every class in a hierarchy; need `__prepare__` |

**Guideline**: prefer `__init_subclass__` and class decorators over metaclasses — they are easier to read, debug, and combine.

## Metaclasses in the Real World
- `abc.ABCMeta` — powers Abstract Base Classes
- Django `ModelBase` — registers model classes and builds ORM machinery
- SQLAlchemy `DeclarativeMeta` — maps Python classes to database tables
- Python 3.7+ features (`__init_subclass__`, `__set_name__`, `dataclasses`) replace many metaclass patterns

## Closing Thoughts
Metaclasses are a stable, powerful feature — but they are rarely the right first choice. `__init_subclass__` handles most "hook into subclass creation" needs without the metaclass protocol overhead. Class decorators handle "transform this class" needs. Reserve metaclasses for framework-level machinery that must apply to an entire class hierarchy transparently. The chapter culminates Fluent Python: having seen the full data model, you can now understand and extend Python itself.
