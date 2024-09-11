import functools
import itertools
import typing as PT

from collections import deque
from collections.abc import Callable, Iterator

import attrs

from typing_extensions import TypeVarTuple


__all__ = ("Seq",)

IterableType1 = PT.TypeVar("IterableType1")
IterableType2 = PT.TypeVar("IterableType2")
IterableType3 = PT.TypeVar("IterableType3")
IterableType4 = TypeVarTuple("IterableType4")
ReturnIterableType1 = PT.TypeVar("ReturnIterableType1")
ReturnIterableType2 = PT.TypeVar("ReturnIterableType2")
ReturnIterableType3 = PT.TypeVar("ReturnIterableType3")


@attrs.frozen(auto_attribs=True, slots=True)
class Seq(Iterator[IterableType1], PT.Generic[IterableType1]):
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
        self: "Seq[tuple[IterableType2, ...]]",
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

    def starmap(
        # py310 not supporting this syntax and we're adding type ignore
        self: "Seq[tuple[*IterableType4]]",  # type: ignore
        func: Callable[[*IterableType4], ReturnIterableType1],
    ) -> "Seq[ReturnIterableType1]":
        return Seq(itertools.starmap(func, self))

    def flatten(
        self: "Seq[tuple[IterableType2, ...]]",
    ) -> "Seq[IterableType2]":
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
                IterableType1,
                IterableType1,
            ],
            IterableType1,
        ],
    ) -> IterableType1:
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
        self: "Seq[IterableType1]",
        seq: "Seq[IterableType2]",
    ) -> "Seq[tuple[IterableType1, IterableType2]]":
        return Seq(zip(self, seq))  # noqa: B905

    def sum(self) -> IterableType1:
        return PT.cast(IterableType1, sum(self))

    def to_tuple(self) -> tuple[IterableType1, ...]:
        return tuple(self)

    def to_list(self) -> list[IterableType1]:
        return list(self)

    def to_dict(
        self: "Seq[tuple[IterableType2, IterableType3]]",
    ) -> dict[IterableType2, IterableType3]:
        return dict(self)

    def exhaust(self) -> None:
        deque(self, 0)

    def consume(self) -> None:
        return self.exhaust()  # pragma: nocover

    def head(self) -> IterableType1:
        return next(self.take())

    def __iter__(  # noqa: PYI034
        self: "Seq[IterableType1]",
    ) -> Iterator[IterableType1]:
        return self

    def __next__(self: "Seq[IterableType1]") -> IterableType1:
        return next(self.some)
