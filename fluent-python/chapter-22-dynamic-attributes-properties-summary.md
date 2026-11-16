# Chapter 22 – Dynamic Attributes and Properties

## Core Idea
Python gives classes fine-grained control over attribute access through `__getattr__`, `__setattr__`, `__getattribute__`, properties, and `__new__`. These mechanisms enable computed attributes, lazy loading, validation, and dynamic data wrangling — all transparently to callers.

## Dynamic Attributes with `__getattr__`
`__getattr__` is called **only when normal lookup fails** (not in `__dict__`, not in class):
```python
class FrozenJSON:
    def __init__(self, mapping):
        self.__data = dict(mapping)

    def __getattr__(self, name):
        try:
            return getattr(self.__data, name)   # delegate to dict methods
        except AttributeError:
            value = self.__data[name]
            if isinstance(value, dict):
                return FrozenJSON(value)        # convert nested dicts
            return value
```

### Invalid Attribute Names
JSON keys can be Python keywords or contain special characters. Escape them:
```python
# keyword clash: feed.class → feed.class_
if keyword.iskeyword(name):
    name += '_'
# non-identifier: feed['123abc'] → feed.get('123abc', ...)
```

## Flexible Object Creation with `__new__`
`__new__` is the actual constructor (called before `__init__`); override it to return a different type:
```python
class FrozenJSON:
    def __new__(cls, arg):
        if isinstance(arg, abc.Mapping):
            return super().__new__(cls)
        elif isinstance(arg, abc.MutableSequence):
            return [cls(item) for item in arg]   # return a list, not a FrozenJSON
        else:
            return arg
```

## Properties for Computed Attributes
```python
class Event:
    def __init__(self, record):
        self.__dict__.update(record)

    @property
    def venue(self):
        key = f'venue.{self.venue_serial}'
        return self.__class__.fetch(key)    # lazy load linked record
```

### Caching with `functools.cached_property`
```python
class Circle:
    def __init__(self, radius):
        self.radius = radius

    @functools.cached_property
    def area(self):
        return math.pi * self.radius ** 2
```
**Caveat**: `cached_property` only works when there is a writable `__dict__`. It does not work with `__slots__` or if the class defines `__set_name__`.

### Alternative: `@property` + `@functools.cache`
```python
class Circle:
    @property
    @functools.cache
    def area(self):
        return math.pi * self.radius ** 2
```

## Validation with Properties
```python
class LineItem:
    def __init__(self, product, quantity, price):
        self.quantity = quantity   # triggers setter
        self.price = price

    @property
    def quantity(self):
        return self.__quantity

    @quantity.setter
    def quantity(self, value):
        if value <= 0:
            raise ValueError('quantity must be > 0')
        self.__quantity = value
```

## Property Factory (for DRY validation)
```python
def quantity(storage_name):
    def qty_getter(instance):
        return instance.__dict__[storage_name]

    def qty_setter(instance, value):
        if value > 0:
            instance.__dict__[storage_name] = value
        else:
            raise ValueError('value must be > 0')

    return property(qty_getter, qty_setter)

class LineItem:
    quantity = quantity('quantity')   # class-level property
    price = quantity('price')
```

## `__getattribute__` vs `__getattr__`
| Method | When called |
|---|---|
| `__getattribute__` | **Every** attribute access (including existing ones); override with care |
| `__getattr__` | Only when normal lookup fails; the safer hook |

## Attribute Handling Summary
| Function | Effect |
|---|---|
| `getattr(obj, name, default)` | Get attribute; calls `__getattribute__` then `__getattr__` |
| `setattr(obj, name, value)` | Set attribute; calls `__setattr__` |
| `delattr(obj, name)` | Delete attribute; calls `__delattr__` |
| `hasattr(obj, name)` | Returns `True` if `getattr` would succeed |
| `vars(obj)` | Returns `obj.__dict__` |
| `dir(obj)` | Returns all attribute names |

## Closing Thoughts
Dynamic attributes blur the line between data and computation. `__getattr__` is the right hook for most dynamic access — it fires only on misses. Properties are the idiomatic Python way to add validation or computation to attribute access while keeping the calling syntax clean. Property factories reduce repetition when multiple attributes need the same logic. `functools.cached_property` gives lazy computation for free when `__dict__` is available.
