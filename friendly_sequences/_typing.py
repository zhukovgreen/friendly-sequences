from __future__ import annotations

from collections.abc import AsyncIterable, Awaitable, Iterable

type AnyIterable[T] = Iterable[T] | AsyncIterable[T]
type MaybeAwaitable[T] = T | Awaitable[T]
