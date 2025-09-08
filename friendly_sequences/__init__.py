from __future__ import annotations

import functools
import itertools
import typing as PT

from collections import deque
from collections.abc import Callable, Iterable, Iterator

import attrs

from typing_extensions import TypeVarTuple, Unpack


__all__ = ("Seq",)

T_co = PT.TypeVar("T_co", covariant=True)
U = PT.TypeVar("U")
V = PT.TypeVar("V")
K = PT.TypeVar("K")
Ts = TypeVarTuple("Ts")


@attrs.frozen(
    auto_attribs=True,
    slots=True,
)
class Seq(Iterator[T_co]):
    """Simple way to build type-safe functions pipelines.

    Example:

    >>> from typing import TypeGuard

    >>> from friendly_sequences import Seq
    >>>
    >>>
    >>> def filter_expr(i: int) -> TypeGuard[int]:
    >>>     return i != 2

    >>> assert (
    >>>     Seq[int]((1, 2))
    >>>     .zip(Seq[int]((3, 4)))
    >>>     .flat_map(lambda x: x + 1)
    >>>     .filter(filter_expr)
    >>>     .sort(reverse=True)
    >>>     .map(str)
    >>>     .fold(lambda left, right: f"{left}{right}", "")
    >>> ) == "543"

    """

    some: Iterator[T_co] = attrs.field(converter=lambda some: iter(some))

    def map(
        self: Seq[T_co],
        func: Callable[[T_co], U],
    ) -> Seq[U]:
        return Seq(map(func, self))

    def flat_map(
        self: Seq[Iterable[V]],
        func: Callable[[V], U],
    ) -> Seq[U]:
        return Seq(
            map(
                func,
                itertools.chain.from_iterable(self),
            )
        )

    def starmap(
        self: Seq[tuple[Unpack[Ts]]],
        func: Callable[[Unpack[Ts]], U],
    ) -> Seq[U]:
        return Seq(itertools.starmap(func, self))

    def flatten(
        self: Seq[tuple[V, ...]],
    ) -> Seq[V]:
        return Seq(itertools.chain.from_iterable(self))

    def filter(
        self: Seq[T_co],
        func: Callable[[T_co], PT.TypeGuard[U] | bool],
    ) -> Seq[U]:
        return Seq(filter(func, self))

    def fold(
        self: Seq[T_co],
        func: Callable[[U, T_co], U],
        initial: U,
    ) -> U:
        return functools.reduce(
            func,
            self,
            initial,
        )

    def reduce(
        self: Seq[T_co],
        func: Callable[[T_co, T_co], T_co],
    ) -> T_co:
        return functools.reduce(
            func,
            self,
        )

    def take(
        self: Seq[T_co],
        n: int = 1,
    ) -> Seq[T_co]:
        return Seq(itertools.islice(self, n))

    def sort(
        self: Seq[T_co],
        *,
        key: None = None,
        reverse: bool = False,
    ) -> Seq[T_co]:
        return Seq(
            sorted(
                self,
                key=key,
                reverse=reverse,
            )
        )

    def zip(
        self: Seq[T_co],
        seq: Iterable[V],
        *,
        strict: bool = False,
    ) -> Seq[tuple[T_co, V]]:
        return Seq(
            zip(
                self,
                seq,
                strict=strict,
            )
        )

    def sum(
        self: Seq[T_co],
    ) -> T_co:
        return PT.cast(T_co, sum(self))

    def to_tuple(
        self: Seq[T_co],
    ) -> tuple[T_co, ...]:
        return tuple(self)

    def to_list(
        self: Seq[T_co],
    ) -> list[T_co]:
        return list(self)

    def to_dict(
        self: Seq[tuple[V, K]],
    ) -> dict[V, K]:
        return dict(self)

    def exhaust(
        self: Seq[T_co],
    ) -> None:
        deque(self, 0)

    def consume(
        self: Seq[T_co],
    ) -> None:
        self.exhaust()  # pragma: nocover

    def head(
        self: Seq[T_co],
    ) -> T_co:
        return next(self.take())

    def join(
        self: Seq[str],
        with_: str = "",
    ) -> str:
        return with_.join(self)

    def all(
        self: Seq[T_co],
    ) -> bool:
        return all(self)

    def any(
        self: Seq[T_co],
    ) -> bool:
        return any(self)

    def __iter__(  # noqa: PYI034
        self: Seq[T_co],
    ) -> Iterator[T_co]:
        return self

    def __next__(
        self: Seq[T_co],
    ) -> T_co:
        return next(self.some)
