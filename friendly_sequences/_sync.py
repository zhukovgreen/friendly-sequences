from __future__ import annotations

import functools
import itertools
import typing as PT

from collections import deque
from collections.abc import Callable, Iterable, Iterator

import attrs

__all__ = ("Seq",)

if PT.TYPE_CHECKING:  # pragma: nocover
    from _typeshed import SupportsRichComparison

    from friendly_sequences._async import AsyncSeq


T_co = PT.TypeVar("T_co", covariant=True)


def _to_iterator[T](some: Iterable[T]) -> Iterator[T]:
    return iter(some)


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

    some: Iterator[T_co] = attrs.field(
        converter=_to_iterator,
    )

    def map[U](
        self,
        func: Callable[[T_co], U],
    ) -> Seq[U]:
        return Seq(map(func, self))

    def flat_map[V, U](
        self: Seq[Iterable[V]],
        func: Callable[[V], U],
    ) -> Seq[U]:
        return Seq(
            map(
                func,
                itertools.chain.from_iterable(self),
            )
        )

    def starmap[*Ts, U](
        self: Seq[tuple[*Ts]],
        func: Callable[[*Ts], U],
    ) -> Seq[U]:
        return Seq(itertools.starmap(func, self))

    def flatten[V](
        self: Seq[tuple[V, ...]],
    ) -> Seq[V]:
        return Seq(itertools.chain.from_iterable(self))

    @PT.overload
    def filter[U](self, func: Callable[[T_co], PT.TypeGuard[U]]) -> Seq[U]: ...

    @PT.overload
    def filter(self, func: Callable[[T_co], bool]) -> Seq[T_co]: ...

    def filter[U](
        self,
        func: Callable[[T_co], PT.TypeGuard[U] | bool],
    ) -> Seq[U]:
        return PT.cast(
            "Seq[U]",
            Seq(item for item in self if func(item)),
        )

    def fold[U](
        self,
        func: Callable[[U, T_co], U],
        initial: U,
    ) -> U:
        return functools.reduce(
            func,
            self,
            initial,
        )

    def reduce(
        self,
        func: Callable[[T_co, T_co], T_co],
    ) -> T_co:
        return functools.reduce(
            func,
            self,
        )

    def take(
        self,
        n: int = 1,
    ) -> Seq[T_co]:
        return Seq(itertools.islice(self, n))

    def sort[S: SupportsRichComparison](
        self: Seq[S],
        *,
        key: None = None,
        reverse: bool = False,
    ) -> Seq[S]:
        return Seq(
            sorted(
                self,
                key=key,
                reverse=reverse,
            )
        )

    def zip[V](
        self,
        *seq: Iterable[V],
        strict: bool = False,
    ) -> Seq[tuple[T_co, V]]:
        return Seq(
            zip(
                self,
                *seq,
                strict=strict,
            )
        )

    def sum(
        self,
    ) -> T_co:
        return PT.cast(T_co, sum(self))

    def to_tuple(
        self,
    ) -> tuple[T_co, ...]:
        return tuple(self)

    def to_list(
        self,
    ) -> list[T_co]:
        return list(self)

    def to_dict[V, K](
        self: Seq[tuple[V, K]],
    ) -> dict[V, K]:
        return dict(self)

    def exhaust(
        self,
    ) -> None:
        deque(self, 0)

    def consume(
        self,
    ) -> None:
        self.exhaust()  # pragma: nocover

    def head(
        self,
    ) -> T_co:
        return next(self.take())

    def join(
        self: Seq[str],
        with_: str = "",
    ) -> str:
        return with_.join(self)

    def all(
        self,
    ) -> bool:
        return all(self)

    def any(
        self,
    ) -> bool:
        return any(self)

    def to_async(
        self,
    ) -> AsyncSeq[T_co]:
        # Runtime import: a module-level one would create a
        # _sync -> _async -> __init__ -> _sync cycle.
        from friendly_sequences._async import AsyncSeq  # noqa: PLC0415

        return AsyncSeq(self)

    def __iter__(  # noqa: PYI034
        self,
    ) -> Iterator[T_co]:
        return self

    def __next__(
        self,
    ) -> T_co:
        return next(self.some)
