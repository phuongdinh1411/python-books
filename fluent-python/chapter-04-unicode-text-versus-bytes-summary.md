# Chapter 4 – Unicode Text Versus Bytes

## Core Idea
**1 character ≠ 1 byte.** Python 3 enforces a hard separation between human-readable text (`str`) and raw binary data (`bytes`/`bytearray`). Understanding encoding and decoding is mandatory for any program that processes text from files, networks, or databases.

## The Character Problem
- A **code point** is a number assigned to a character: `U+0041` → `'A'`
- An **encoding** maps code points to bytes: UTF-8, UTF-16, Latin-1, etc.
- **Encoding** converts `str → bytes`; **decoding** converts `bytes → str`

```python
s = 'café'
b = s.encode('utf8')   # b'caf\xc3\xa9'  — 5 bytes, 4 chars
b.decode('utf8')       # 'café'
```

## Binary Sequence Types
| Type | Mutable? | Use |
|---|---|---|
| `bytes` | No | Immutable binary data |
| `bytearray` | Yes | Mutable binary buffer |
| `memoryview` | — | Zero-copy view over bytes-like object |

Each element of `bytes`/`bytearray` is an integer 0–255. Slices return the same type; single indexing returns `int`.

## Common Encodings
| Codec | Key facts |
|---|---|
| `utf-8` | Variable 1–4 bytes; ASCII-compatible; most common on the web |
| `utf-16` | 2–4 bytes; BOM used to signal byte order |
| `latin-1` / `iso8859-1` | Single byte; Western European |
| `cp1252` | Windows default for Western European; superset of Latin-1 |
| `ascii` | 7-bit; 128 code points only |

## Handling Encode/Decode Errors
```python
# Encoding errors
'São Paulo'.encode('ascii')             # UnicodeEncodeError
'São Paulo'.encode('ascii', errors='ignore')   # b'So Paulo'
'São Paulo'.encode('ascii', errors='replace')  # b'S?o Paulo'
'São Paulo'.encode('ascii', errors='xmlcharrefreplace')  # b'S&#227;o Paulo'

# Decoding errors
b'\x80abc'.decode('utf-8', errors='replace')   # '?abc'
b'\x80abc'.decode('utf-8', errors='ignore')    # 'abc'
```
Source file encoding: add `# -*- coding: utf-8 -*-` or declare encoding in the shebang.

## Detecting Encoding
There is **no reliable algorithmic way** to detect encoding from bytes alone. The `chardet` library heuristically detects encodings for common formats. **Byte Order Marks (BOM)** (`\xff\xfe` for UTF-16-LE) provide a hint but are not universal.

## The Unicode Sandwich
Best practice for programs handling text:

```
Bytes in → decode as early as possible
                ↓
    Work only with str internally
                ↓
Encode to bytes as late as possible → Bytes out
```

Always specify `encoding=` when opening text files:
```python
open('data.txt', encoding='utf-8')  # explicit; portable
open('data.txt')                    # uses locale default; fragile on Windows
```

## Unicode Normalisation
The same visual character can have multiple representations:
- `'café'` — `c`, `a`, `f`, `é` (1 code point)
- `'café'` — `c`, `a`, `f`, `e`, `◌́` (combining accent, 2 code points)

```python
import unicodedata
s1 = 'café'
s2 = 'cafe\u0301'
s1 == s2   # False — different code points
unicodedata.normalize('NFC', s1) == unicodedata.normalize('NFC', s2)  # True
```

**Normal forms:**
- `NFC` — compose; shortest equivalent form (preferred for text storage)
- `NFD` — decompose; split into base + combining marks
- `NFKC` / `NFKD` — also fold compatibility characters (e.g. `ﬁ` → `fi`)

For case-insensitive matching use `str.casefold()` (more thorough than `.lower()`).

## Sorting Unicode Text
```python
import locale
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
sorted(fruits, key=locale.strxfrm)   # locale-aware sort

# Or use PyICU / icu.Collator for portable Unicode-correct sorting
```

## `str` vs `bytes` in APIs
- `re` patterns: compile with `str` patterns for text; `bytes` patterns for binary
- `os` functions: accept both; pass `bytes` only when handling non-decodable filenames
- `os.fsencode()` / `os.fsdecode()` — bridge between `str` paths and filesystem bytes

## Closing Thoughts
Every program that touches text outside pure ASCII must understand encoding. The three most common mistakes are: not specifying encoding when opening files, assuming UTF-8 is always safe, and neglecting Unicode normalisation before comparing strings. The Unicode sandwich pattern prevents most encoding bugs by confining bytes to the I/O boundary.
