# Python Books — Fast Learning Guide

Chapter summaries for five books, organized to help you understand the main ideas and then apply them. These are learning notes, not replacements for the books or a verified reproduction of every chapter.

## Choose a Book

| Your goal | Start here | Main lesson | Prerequisites |
|---|---|---|---|
| Move beyond basic Python | [Powerful Python](powerful-python/README.md) | Compose iterators, functions, and classes into reusable programs | Functions, loops, basic classes |
| Write more idiomatic Python | [Effective Python](effective-python/README.md) | Small API and implementation choices prevent common mistakes | Comfortable reading everyday Python |
| Make a growing codebase safer | [Robust Python](robust-python/README.md) | Communicate intent through types, contracts, boundaries, and tests | Functions, classes, basic testing |
| Make slow or memory-heavy code faster | [High Performance Python](high-performance-python/README.md) | Measure first; improve algorithms and data layout before scaling | Intermediate Python; NumPy helps |
| Understand concurrent network programs | [Using Asyncio in Python](using-asyncio-python/README.md) | Overlap I/O using cooperative tasks with explicit lifetime and cancellation | Iterators, exceptions, context managers |

**Suggested order:** Powerful Python → Effective Python → Robust Python. Then choose High Performance Python or Using Asyncio based on a real project need. You do not need to read all five in order.

## How to Use the Summaries

1. **Orient:** read a book guide's one-minute overview and mental model.
2. **Prioritize:** follow its quick route instead of reading every chapter equally.
3. **Learn:** skim a chapter's Core Idea/Overview and closing takeaways, then read the relevant example and trade-offs.
4. **Practice:** complete the guide's small exercise. Predict behavior before running code.
5. **Retrieve:** answer the self-check without looking. If you cannot explain the trade-off, revisit that chapter or the original book.

Reading alone builds familiarity; explaining and changing working code builds usable knowledge. Route time estimates are approximate skim times, excluding practice.

## Find a Topic Across Books

| Topic | First explanation | Deeper follow-up |
|---|---|---|
| Iterators and lazy pipelines | [Powerful, Ch. 1](powerful-python/chapter-01-scaling-with-generators-summary.md) | [Effective, Ch. 4](effective-python/chapter-04-comprehensions-and-generators-summary.md); [Performance, Ch. 5](high-performance-python/chapter-05-iterators-and-generators-summary.md) |
| Function APIs and decorators | [Powerful, Ch. 3](powerful-python/chapter-03-advanced-functions-summary.md) | [Effective, Ch. 3](effective-python/chapter-03-functions-summary.md) |
| Types and domain models | [Robust, Ch. 4](robust-python/chapter-04-constraining-types-summary.md) | [Robust, Ch. 9](robust-python/chapter-09-user-defined-types-data-classes-summary.md) and [Ch. 13](robust-python/chapter-13-protocols-summary.md) |
| Choosing concurrency | [Effective, Ch. 7](effective-python/chapter-07-concurrency-and-parallelism-summary.md) | [Asyncio, Ch. 3](using-asyncio-python/chapter-03-asyncio-walkthrough-summary.md); [Performance, Ch. 10](high-performance-python/chapter-10-multiprocessing-summary.md) |
| Profiling and memory | [Performance, Ch. 2](high-performance-python/chapter-02-profiling-to-find-bottlenecks-summary.md) | [Performance, Ch. 12](high-performance-python/chapter-12-using-less-ram-summary.md) |
| Test quality | [Powerful, Ch. 7](powerful-python/chapter-07-automated-testing-summary.md) | [Robust, Ch. 21–24](robust-python/README.md#chapter-map) |
| Interfaces and dependencies | [Robust, Ch. 11](robust-python/chapter-11-defining-your-interfaces-summary.md) | [Robust, Ch. 16](robust-python/chapter-16-dependencies-summary.md) and [Ch. 19](robust-python/chapter-19-pluggable-python-summary.md) |

## Version and Example Conventions

- **Book editions:** the High Performance Python notes identify the third edition; the Effective Python notes follow the 90-item, second-edition structure. Other editions are not recorded in the existing notes and still need confirmation against your copies.
- **Modern additions:** these notes mix book-era material with later Python/library features. Version notes distinguish major updates where identified; not every addition has been traced to the original text.
- **Recommended practice baseline:** Python 3.11+ for `TaskGroup`, `asyncio.timeout`, and `typing.Self`; Pydantic examples in Chapter 14 now target v2. Other libraries may require particular versions.
- **GIL advice:** unless stated otherwise, assume GIL-enabled CPython. Optional free-threaded builds exist from 3.13, and native libraries can release the GIL even on ordinary builds.
- **Code blocks:** many are sketches, not standalone scripts. Names such as `fetch_url`, `MenuItem`, and `raw_dict` stand for application code/data. Supply imports, dependencies, and input fixtures before running them. The short examples in the book guides use only the standard library.
- **Performance numbers:** treat existing tables as illustrative reported results, not promises or independently reproduced measurements. Hardware, input, library versions, warm-up, and numerical equivalence matter.

## Review Status

All 61 chapter summaries received an editorial/technical pass. Clear errors were corrected and book-level reading guides added. The remaining limitation is **source fidelity**: no source books or benchmark artifacts are present here, so completeness, quotations, exact timings, and edition alignment are not certified.

See [SUMMARY_REVIEW.md](SUMMARY_REVIEW.md) for findings, corrections, and follow-up priorities.
