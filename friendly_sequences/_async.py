from __future__ import annotations

import asyncio
import contextlib
import inspect
import typing as PT

from collections import deque
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

    def sort[S: SupportsRichComparison](
        self: AsyncSeq[S],
        *,
        key: None = None,
        reverse: bool = False,
    ) -> AsyncSeq[S]:
        """Sort, draining lazily on the first ``__anext__``.

        This stays a plain (non-``async def``) method returning an
        ``AsyncSeq``: draining needs ``await``, but ``async def sort``
        would return a coroutine instead of an ``AsyncSeq`` and break the
        fluent chain (``await (await seq.sort()).to_list()``). Forced by
        async, not a style choice.

        ``S`` carries ``sorted()``'s ``SupportsRichComparison`` bound so
        the body type-checks without casts. Note this documents intent
        rather than guarding callers: mypy solves ``S`` from the element
        type without enforcing the bound through the self-type, so
        ``AsyncSeq[Unsortable].sort()`` still type-checks and fails at
        runtime, exactly as ``Seq.sort`` does.
        """

        async def gen() -> AsyncIterator[S]:
            async with _closing(self.some) as upstream:
                items = [item async for item in upstream]
            for sorted_item in sorted(items, key=key, reverse=reverse):
                yield sorted_item

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

    @PT.overload
    def map_concurrent[U](
        self,
        func: Callable[[T_co], Awaitable[U]],
        limit: int = 10,
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def map_concurrent[U](
        self,
        func: Callable[[T_co], U],
        limit: int = 10,
    ) -> AsyncSeq[U]: ...

    def map_concurrent[U](
        self,
        func: Callable[[T_co], MaybeAwaitable[U]],
        limit: int = 10,
    ) -> AsyncSeq[U]:
        """Bounded, order-preserving, streaming concurrent map.

        Keeps a sliding window of at most ``limit`` in-flight tasks; the
        input is never materialized. Results are yielded in input order
        even though they may complete out of order, so a slow early item
        holds up faster later ones exactly as a bounded ``asyncio.gather``
        would.

        Early exit (``aclose()``, breaking out of a consuming loop, or
        ``.take(n)`` upstream of this stage) cancels every pending task and
        awaits their cancellation before returning, so no task leaks past
        this generator's lifetime.
        """

        async def gen() -> AsyncIterator[U]:
            sem = asyncio.Semaphore(limit)

            async def run[V](
                item: V,
                mapper: Callable[[V], MaybeAwaitable[U]],
            ) -> U:
                async with sem:
                    return await _resolve(mapper(item))

            pending: deque[asyncio.Task[U]] = deque()
            async with _closing(self.some) as src:
                try:
                    while True:
                        while len(pending) < limit:
                            try:
                                item = await anext(src)
                            except StopAsyncIteration:
                                break
                            pending.append(
                                asyncio.create_task(run(item, func))
                            )
                        if not pending:
                            return
                        yield await pending.popleft()
                finally:
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)

        return AsyncSeq(gen())

    @PT.overload
    def map_unordered[U](
        self,
        func: Callable[[T_co], Awaitable[U]],
        limit: int = 10,
    ) -> AsyncSeq[U]: ...

    @PT.overload
    def map_unordered[U](
        self,
        func: Callable[[T_co], U],
        limit: int = 10,
    ) -> AsyncSeq[U]: ...

    def map_unordered[U](
        self,
        func: Callable[[T_co], MaybeAwaitable[U]],
        limit: int = 10,
    ) -> AsyncSeq[U]:
        """Bounded, completion-order, streaming concurrent map.

        Same sliding window as ``map_concurrent``, but yields each result
        as soon as it finishes rather than preserving input order — better
        tail latency, no ordering guarantee. Early exit cancels every
        pending task the same way ``map_concurrent`` does.
        """

        async def gen() -> AsyncIterator[U]:
            sem = asyncio.Semaphore(limit)

            async def run[V](
                item: V,
                mapper: Callable[[V], MaybeAwaitable[U]],
            ) -> U:
                async with sem:
                    return await _resolve(mapper(item))

            pending: set[asyncio.Task[U]] = set()
            async with _closing(self.some) as src:
                try:
                    while True:
                        while len(pending) < limit:
                            try:
                                item = await anext(src)
                            except StopAsyncIteration:
                                break
                            pending.add(asyncio.create_task(run(item, func)))
                        if not pending:
                            return
                        done, pending = await asyncio.wait(
                            pending,
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for task in done:
                            yield task.result()
                finally:
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)

        return AsyncSeq(gen())

    def chunked(
        self,
        n: int,
    ) -> AsyncSeq[tuple[T_co, ...]]:
        """Group elements into fixed-size, immutable ``tuple`` chunks.

        Yields ``tuple``, not ``list`` — symmetry with ``flatten`` over an
        ``AsyncSeq[tuple[V, ...]]`` and with ``to_tuple``. Chain
        ``.chunked(n).map(list)`` where a mutable buffer is actually
        needed; there is no separate mutable variant. A short final chunk
        is yielded, not dropped.

        Stays a plain (non-``async def``) method returning an ``AsyncSeq``,
        the same reasoning as ``sort``: buffering the next chunk needs
        ``await``, but ``async def chunked`` would return a coroutine
        instead of an ``AsyncSeq`` and break the fluent chain.
        """

        async def gen() -> AsyncIterator[tuple[T_co, ...]]:
            buffer: list[T_co] = []
            async with _closing(self.some) as upstream:
                async for item in upstream:
                    buffer.append(item)
                    if len(buffer) == n:
                        yield tuple(buffer)
                        buffer = []
            if buffer:
                yield tuple(buffer)

        return AsyncSeq(gen())

    def throttle(
        self,
        per_second: float,
    ) -> AsyncSeq[T_co]:
        """Yield at most ``per_second`` items per second.

        Enforces a minimum interval between yields using the running event
        loop's own clock (``loop.time()``), not ``time.time()``, so tests
        can reason about elapsed time against the same clock
        ``asyncio.sleep`` uses.
        """

        async def gen() -> AsyncIterator[T_co]:
            interval = 1 / per_second
            loop = asyncio.get_running_loop()
            last_yielded_at: float | None = None
            async with _closing(self.some) as upstream:
                async for item in upstream:
                    now = loop.time()
                    if last_yielded_at is not None:
                        elapsed = now - last_yielded_at
                        if elapsed < interval:
                            await asyncio.sleep(interval - elapsed)
                    last_yielded_at = loop.time()
                    yield item

        return AsyncSeq(gen())

    def timeout(
        self,
        total: float | None = None,
        per_item: float | None = None,
    ) -> AsyncSeq[T_co]:
        """Bound the stream's total duration and/or the wait for each item.

        ``total`` wraps the whole stream in ``asyncio.timeout``; ``per_item``
        wraps each ``anext()`` in its own nested ``asyncio.timeout``. Both
        are optional and independently usable.

        A firing ``per_item`` timeout can leave the upstream source
        half-consumed — a coroutine cancelled mid-request — so a caller
        that catches the resulting ``TimeoutError`` should ``aclose()``
        this ``AsyncSeq`` to let the source clean up.
        """

        async def gen() -> AsyncIterator[T_co]:
            async with _closing(self.some) as upstream:
                async with asyncio.timeout(total):
                    while True:
                        try:
                            async with asyncio.timeout(per_item):
                                item = await anext(upstream)
                        except StopAsyncIteration:
                            return
                        yield item

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
