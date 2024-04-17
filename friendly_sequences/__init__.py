import functools
import itertools
import typing as PT

from collections.abc import Callable, Iterator

import attrs


__all__ = ("Seq",)

IterableType1 = PT.TypeVar("IterableType1")
IterableType2 = PT.TypeVar("IterableType2")
ReturnIterableType1 = PT.TypeVar("ReturnIterableType1")
ReturnIterableType2 = PT.TypeVar("ReturnIterableType2")


@attrs.frozen(auto_attribs=True, slots=True)
class Seq(Iterator, PT.Generic[IterableType1]):
    some: Iterator[IterableType1] = attrs.field(
        converter=lambda some: iter(some)
    )

    def map(
        self,
        func: Callable[
            [IterableType1],
            ReturnIterableType1,
        ],
    ) -> "Seq[ReturnIterableType1]":
        return Seq(map(func, self))

    def flat_map(
        self,
        func: Callable[
            [IterableType2],
            ReturnIterableType2,
        ],
    ) -> "Seq[ReturnIterableType2]":
        return Seq(
            map(
                func,
                itertools.chain.from_iterable(self),
            )
        )

    def flatten(
        self,
    ) -> "Seq[ReturnIterableType1]":
        return Seq(itertools.chain.from_iterable(self))

    def filter(
        self, func: Callable[[IterableType1], bool]
    ) -> "Seq[IterableType1]":
        return Seq(filter(func, self))

    def fold(
        self,
        func: Callable[
            [
                ReturnIterableType1,
                IterableType1,
            ],
            ReturnIterableType1,
        ],
        initial: ReturnIterableType1,
    ) -> ReturnIterableType1:
        return functools.reduce(
            func,
            self,
            initial,
        )

    def reduce(
        self,
        func: Callable[
            [
                ReturnIterableType1,
                IterableType1,
            ],
            ReturnIterableType1,
        ],
    ) -> ReturnIterableType1:
        return functools.reduce(
            func,
            self,
        )

    def take(self, n: int = 1) -> "Seq[IterableType1]":
        return Seq(itertools.islice(self, n))

    def sort(
        self,
        *,
        key: None = None,
        reverse: bool = False,
    ) -> "Seq[IterableType1]":
        return Seq(
            sorted(
                self,
                key=key,
                reverse=reverse,
            )
        )

    def zip(
        self,
        seq: "Seq[IterableType2]",
    ) -> "Seq[tuple[IterableType1, IterableType2]]":
        return Seq(zip(self, seq, strict=False))

    def sum(self) -> IterableType1:
        return PT.cast(IterableType1, sum(self))

    def to_tuple(self) -> tuple[IterableType1, ...]:
        return tuple(self)

    def to_list(self) -> list[IterableType1]:
        return list(self)

    def head(self) -> IterableType1:
        return next(self.take())

    def __iter__(self) -> "Seq[IterableType1]":
        return self

    def __next__(self) -> IterableType1:
        return next(self.some)
