# Friendly Sequences

Inspired by Scala Sequence class [1] and iterchain [2],
but with a good typing support.

[1] https://alvinalexander.com/scala/seq-class-methods-examples-syntax/
[2] https://github.com/Evelyn-H/iterchain

## Motivation

It is possible to compose functions in python with many functional
programming primitives, like map, filter, reduce etc. But, in my opinion,
looks a bit ugly and you need to get use to this structure. For example, you
can write something like this:

```python
import itertools

from functools import reduce

assert (
    reduce(
        lambda left, right: f"{left}{right}",
        map(
            str,
            sorted(
                filter(
                    lambda x: x != 2,
                    map(
                        lambda x: x + 1,
                        itertools.chain.from_iterable(
                            zip(
                                (1, 2),
                                (3, 4),
                            )
                        ),
                    ),
                )
            ),
        ),
        "",
    )
    == "345"
)
```

or even this:

```python
import itertools

assert (
    "".join(
        sorted(
            str(x)
            for x in (
                x
                for x in (
                    x + 1
                    for x in itertools.chain.from_iterable(
                        zip(
                            (1, 2),
                            (3, 4),
                        )
                    )
                )
                if x != 2
            )
        )
    )
    == "345"
)
```

but with the friendly-sequences it is just this:

```python
from friendly_sequences import Seq

assert (
    Seq[int]((1, 2))
    .zip(Seq[int]((3, 4)))
    .flat_map(lambda x: x + 1)
    .filter(lambda x: x != 2)
    .sort()
    .map(str)
    .fold(lambda left, right: f"{left}{right}", "")
) == "345"
```

## Async

The moment a stage in the pipeline does I/O, the chain breaks down and you
fall back to hand-rolled asyncio — which is the same nested shape all over
again:

```python
import asyncio

async def fetch_all(urls):
    semaphore = asyncio.Semaphore(20)

    async def fetch_one(url):
        async with semaphore:
            return await fetch(url)

    return [
        result
        for result in await asyncio.gather(
            *(fetch_one(url) for url in urls if is_valid(url))
        )
        if result is not None
    ]
```

`AsyncSeq` keeps it a chain:

```python
from friendly_sequences import Seq

results = await (
    Seq(urls)
    .filter(is_valid)
    .to_async()
    .map_concurrent(fetch, limit=20)
    .filter(lambda result: result is not None)
    .to_list()
)
```

The two are not quite equivalent, and the difference is the point:
`asyncio.gather` builds a task per URL up front, so a million URLs is a
million tasks. `map_concurrent` keeps a sliding window of at most `limit`
in-flight tasks and never materializes the input.

Every operator takes either a plain or an `async` callable, so you rarely
have to think about which you have:

```python
from friendly_sequences import AsyncSeq

async def double(x: int) -> int:
    return x * 2

assert await AsyncSeq((1, 2, 3)).map(double).sum() == 12
assert await AsyncSeq((1, 2, 3)).map(str).join("-") == "1-2-3"
```

`AsyncSeq` mirrors the whole `Seq` surface — `map`, `flat_map`, `starmap`,
`flatten`, `filter`, `take`, `sort`, `zip`, and the terminals — with two
differences: combinators return an `AsyncSeq`, and every terminal is a
coroutine you `await`.

### Concurrency operators

These have no `Seq` counterpart:

| Operator                           | Behaviour                                                          |
|------------------------------------|--------------------------------------------------------------------|
| `map_concurrent(func, limit=10)`   | Bounded concurrent map, results in **input order**                 |
| `map_unordered(func, limit=10)`    | Same window, results in **completion order** — better tail latency |
| `chunked(n)`                       | Batches into `tuple`s of up to `n`; a short final batch is kept    |
| `throttle(per_second)`             | Minimum interval between yields                                    |
| `timeout(total=..., per_item=...)` | Bounds the whole stream, each item, or both                        |

### Things worth knowing

**Clean up early exits with `aclose()`.** If you abandon a pipeline before
it is exhausted, call `aclose()` on it. Each stage closes its own upstream,
so one call finalizes the whole chain and cancels any in-flight work.
Consuming a pipeline to exhaustion needs no cleanup.

```python
pipeline = AsyncSeq(urls).map_concurrent(fetch, limit=20)
first = await anext(pipeline)
await pipeline.aclose()
```

**A firing `per_item` timeout can leave the source half-consumed** — a
coroutine cancelled mid-request. If you catch the `TimeoutError` and intend
to carry on, `aclose()` the sequence.

**`sort` and `chunked` are not `async def`**, even though they buffer. They
return an `AsyncSeq` that drains on first use, so the chain keeps reading
left to right instead of becoming `await (await seq.sort()).to_list()`.

**`AsyncSeq` is pull-based.** For backpressure-aware streaming, use a
channel library.

## Installation

```bash
$ pip install friendly-sequences
```

Requires Python 3.12 or newer.
