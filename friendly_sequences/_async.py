from __future__ import annotations

import contextlib
import inspect
import typing as PT

from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
)

import attrs

# Gating these behind `if TYPE_CHECKING:` would leave `_typing.py` never
# imported at runtime, tripping the 100% coverage gate on its own module.
from friendly_sequences._typing import AnyIterable  # noqa: TC001
from friendly_sequences._typing import MaybeAwaitable  # noqa: TC001

if PT.TYPE_CHECKING:  # pragma: nocover
    from _typeshed import SupportsRichComparison

__all__ = ("AsyncSeq",)

T_co = PT.TypeVar("T_co", covariant=True)


def _to_async_iterator[T](some: AnyIterable[T]) -> AsyncIterator[T]:
    if isinstance(some, AsyncIterable):
        return aiter(some)
    return _from_sync(some)


async def _from_sync[T](some: Iterable[T]) -> AsyncIterator[T]:
    for item in some:
        yield item


async def _resolve[T](value: MaybeAwaitable[T]) -> T:
    return await value if inspect.isawaitable(value) else value


@contextlib.asynccontextmanager
async def _closing[T](
    source: AnyIterable[T],
) -> AsyncIterator[AsyncIterator[T]]:
    """Guarantee ``aclose()`` on an upstream source.

    Async iterators are not required to be closeable; async generators
    are. ``async for`` never calls ``aclose()`` on what it iterates, so
    without this every combinator would leak upstream generators to the
    event loop's non-deterministic asyncgen-finalization hooks instead of
    closing them the moment a consumer stops pulling.
    """
    iterator = _to_async_iterator(source)
    try:
        yield iterator
    finally:
        if (aclose := getattr(iterator, "aclose", None)) is not None:
            await aclose()


@attrs.frozen(
    auto_attribs=True,
    slots=True,
)
class AsyncSeq(AsyncIterator[T_co]):
    """Async mirror of ``Seq``, for pipeline stages that need to do I/O.

    Same idiom as ``Seq``: lazy combinators return a new ``AsyncSeq``, and
    ``self:``-narrowing types the element shape where it changes. Two
    differences: every operator accepts both plain and async callables,
    and every terminal operation is a coroutine.

    Example:

    >>> from friendly_sequences import AsyncSeq
    >>>
    >>>
    >>> async def main() -> None:
    >>>     async def double(i: int) -> int:
    >>>         return i * 2
    >>>
    >>>     assert (
    >>>         await AsyncSeq[int]((1, 2, 3)).map(double).sum()
    >>>     ) == 12

    """

    some: AsyncIterator[T_co] = attrs.field(
        converter=_to_async_iterator,
    )

    @PT.overload
    def map[U](
        self,
        func: Callable[[T_co], Awaitable[U]],
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def map[U](
        self,
        func: Callable[[T_co], U],
    ) -> AsyncSeq[U]: ...

    def map[U](
        self,
        func: Callable[[T_co], MaybeAwaitable[U]],
    ) -> AsyncSeq[U]:
        async def gen() -> AsyncIterator[U]:
            async with _closing(self.some) as upstream:
                async for item in upstream:
                    yield await _resolve(func(item))

        return AsyncSeq(gen())

    @PT.overload
    def flat_map[V, U](
        self: AsyncSeq[Iterable[V]],
        func: Callable[[V], Awaitable[U]],
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def flat_map[V, U](
        self: AsyncSeq[Iterable[V]],
        func: Callable[[V], U],
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def flat_map[V, U](
        self: AsyncSeq[AsyncIterable[V]],
        func: Callable[[V], Awaitable[U]],
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def flat_map[V, U](
        self: AsyncSeq[AsyncIterable[V]],
        func: Callable[[V], U],
    ) -> AsyncSeq[U]: ...

    def flat_map[V, U](
        self: AsyncSeq[AnyIterable[V]],
        func: Callable[[V], MaybeAwaitable[U]],
    ) -> AsyncSeq[U]:
        async def gen() -> AsyncIterator[U]:
            async with _closing(self.some) as upstream:
                async for sub in upstream:
                    async with _closing(sub) as inner:
                        async for item in inner:
                            yield await _resolve(func(item))

        return AsyncSeq(gen())

    @PT.overload
    def starmap[*Ts, U](
        self: AsyncSeq[tuple[*Ts]],
        func: Callable[[*Ts], Awaitable[U]],
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def starmap[*Ts, U](
        self: AsyncSeq[tuple[*Ts]],
        func: Callable[[*Ts], U],
    ) -> AsyncSeq[U]: ...

    def starmap[*Ts, U](
        self: AsyncSeq[tuple[*Ts]],
        func: Callable[[*Ts], MaybeAwaitable[U]],
    ) -> AsyncSeq[U]:
        async def gen() -> AsyncIterator[U]:
            async with _closing(self.some) as upstream:
                async for item in upstream:
                    yield await _resolve(func(*item))

        return AsyncSeq(gen())

    @PT.overload
    def flatten[V](
        self: AsyncSeq[Iterable[V]],
    ) -> AsyncSeq[V]: ...

    @PT.overload
    def flatten[V](
        self: AsyncSeq[AsyncIterable[V]],
    ) -> AsyncSeq[V]: ...

    def flatten[V](
        self: AsyncSeq[AnyIterable[V]],
    ) -> AsyncSeq[V]:
        async def gen() -> AsyncIterator[V]:
            async with _closing(self.some) as upstream:
                async for sub in upstream:
                    async with _closing(sub) as inner:
                        async for item in inner:
                            yield item

        return AsyncSeq(gen())

    @PT.overload
    def filter[U](
        self,
        func: Callable[[T_co], PT.TypeGuard[U]],
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def filter(
        self,
        func: Callable[[T_co], Awaitable[bool]],
    ) -> AsyncSeq[T_co]: ...

    @PT.overload
    def filter(
        self,
        func: Callable[[T_co], bool],
    ) -> AsyncSeq[T_co]: ...

    def filter[U](
        self,
        func: Callable[[T_co], PT.TypeGuard[U] | Awaitable[bool] | bool],
    ) -> AsyncSeq[U]:
        async def gen() -> AsyncIterator[U]:
            async with _closing(self.some) as upstream:
                async for item in upstream:
                    if await _resolve(func(item)):
                        yield PT.cast(U, item)

        return AsyncSeq(gen())

    async def fold[U](
        self,
        func: Callable[[U, T_co], MaybeAwaitable[U]],
        initial: U,
    ) -> U:
        result = initial
        async with _closing(self.some) as upstream:
            async for item in upstream:
                result = await _resolve(func(result, item))
        return result

    async def reduce(
        self,
        func: Callable[[T_co, T_co], MaybeAwaitable[T_co]],
    ) -> T_co:
        async with _closing(self.some) as upstream:
            try:
                result = await anext(upstream)
            except StopAsyncIteration:
                raise TypeError(
                    "reduce() of empty iterable with no initial value"
                ) from None
            async for item in upstream:
                result = await _resolve(func(result, item))
        return result

    def take(
        self,
        n: int = 1,
    ) -> AsyncSeq[T_co]:
        async def gen() -> AsyncIterator[T_co]:
            async with _closing(self.some) as upstream:
                for _ in range(n):
                    try:
                        yield await anext(upstream)
                    except StopAsyncIteration:
                        return

        return AsyncSeq(gen())

    def sort(
        self,
        *,
        key: None = None,
        reverse: bool = False,
    ) -> AsyncSeq[T_co]:
        """Sort, draining lazily on the first ``__anext__``.

        This stays a plain (non-``async def``) method returning an
        ``AsyncSeq``: draining needs ``await``, but ``async def sort``
        would return a coroutine instead of an ``AsyncSeq`` and break the
        fluent chain (``await (await seq.sort()).to_list()``). Forced by
        async, not a style choice.

        ``AsyncSeq``'s converter is a named, typed function, unlike
        ``Seq``'s untyped-lambda one, so mypy actually enforces
        ``sorted()``'s ``SupportsRichComparison`` bound here instead of
        silently treating it as unconstrained. The cast below is the same
        kind of escape hatch ``Seq.sum`` already uses for the equivalent
        gap in ``sum()``'s builtin signature.
        """

        async def gen() -> AsyncIterator[T_co]:
            async with _closing(self.some) as upstream:
                items = [item async for item in upstream]
            ordered = sorted(
                PT.cast("list[SupportsRichComparison]", items),
                key=key,
                reverse=reverse,
            )
            for sorted_item in ordered:
                yield PT.cast(T_co, sorted_item)

        return AsyncSeq(gen())

    def zip[V](
        self,
        *seq: AnyIterable[V],
        strict: bool = False,
    ) -> AsyncSeq[tuple[T_co, V]]:
        async def gen() -> AsyncIterator[tuple[T_co, V]]:
            sources: tuple[AnyIterable[T_co | V], ...] = (self.some, *seq)
            async with contextlib.AsyncExitStack() as stack:
                iterators: list[AsyncIterator[T_co | V]] = [
                    await stack.enter_async_context(_closing(source))
                    for source in sources
                ]
                items: list[T_co | V] = []
                while True:
                    items = []
                    for iterator in iterators:
                        try:
                            items.append(await anext(iterator))
                        except StopAsyncIteration:
                            break
                    if len(items) < len(iterators):
                        break
                    yield PT.cast(tuple[T_co, V], tuple(items))
                if not strict:
                    return
                if items:
                    plural = " " if len(items) == 1 else "s 1-"
                    raise ValueError(
                        f"zip() argument {len(items) + 1} is shorter "
                        f"than argument{plural}{len(items)}"
                    )
                for index, iterator in enumerate(iterators[1:], 1):
                    try:
                        await anext(iterator)
                    except StopAsyncIteration:
                        continue
                    plural = " " if index == 1 else "s 1-"
                    raise ValueError(
                        f"zip() argument {index + 1} is longer "
                        f"than argument{plural}{index}"
                    )

        return AsyncSeq(gen())

    async def sum(
        self,
    ) -> T_co:
        async with _closing(self.some) as upstream:
            items = [item async for item in upstream]
        return PT.cast(T_co, sum(items))

    async def to_tuple(
        self,
    ) -> tuple[T_co, ...]:
        return tuple(await self.to_list())

    async def to_list(
        self,
    ) -> list[T_co]:
        async with _closing(self.some) as upstream:
            return [item async for item in upstream]

    async def to_dict[V, K](
        self: AsyncSeq[tuple[V, K]],
    ) -> dict[V, K]:
        async with _closing(self.some) as upstream:
            return {key: value async for key, value in upstream}

    async def exhaust(
        self,
    ) -> None:
        async with _closing(self.some) as upstream:
            async for _ in upstream:
                pass

    async def consume(
        self,
    ) -> None:
        await self.exhaust()  # pragma: nocover

    async def head(
        self,
    ) -> T_co:
        taken = self.take()
        try:
            return await anext(taken)
        finally:
            await taken.aclose()

    async def join(
        self: AsyncSeq[str],
        with_: str = "",
    ) -> str:
        async with _closing(self.some) as upstream:
            return with_.join([item async for item in upstream])

    async def all(
        self,
    ) -> bool:
        async with _closing(self.some) as upstream:
            async for item in upstream:
                if not item:
                    return False
        return True

    async def any(
        self,
    ) -> bool:
        async with _closing(self.some) as upstream:
            async for item in upstream:
                if item:
                    return True
        return False

    def __aiter__(  # noqa: PYI034
        self,
    ) -> AsyncIterator[T_co]:
        return self

    async def __anext__(
        self,
    ) -> T_co:
        return await anext(self.some)

    async def aclose(
        self,
    ) -> None:
        if (aclose := getattr(self.some, "aclose", None)) is not None:
            await aclose()
