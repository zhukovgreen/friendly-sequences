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

## Installation

```bash
$ pip install friendly-sequences
```
