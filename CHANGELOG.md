# Changelog

## 2.0

### Breaking

- **Python 3.10 and 3.11 are no longer supported.** `requires-python` is now
  `>=3.12`. The floor buys `asyncio.timeout` and `TaskGroup` (3.11) and PEP 695
  generics and `type` aliases (3.12), which the async API is built on. Installs
  on 3.10 and 3.11 will resolve to 1.x. CI covers 3.12, 3.13 and 3.14.

### Added

- **`AsyncSeq`** — an async mirror of `Seq` for pipelines that do I/O. It covers
  the whole `Seq` surface, with combinators returning an `AsyncSeq` and every
  terminal a coroutine. Operators accept plain *and* `async` callables
  interchangeably.
- **Concurrency operators**, which have no `Seq` counterpart:
  `map_concurrent(func, limit=10)` (bounded, input order),
  `map_unordered(func, limit=10)` (bounded, completion order),
  `chunked(n)`, `throttle(per_second)` and
  `timeout(total=..., per_item=...)`. Both concurrent maps keep a sliding
  window of at most `limit` in-flight tasks and never materialize the input,
  unlike an `asyncio.gather` over the whole source.
- **`AsyncSeq.aclose()`** — abandoning a pipeline early finalizes the whole
  chain and cancels in-flight work. Each stage closes its own upstream, so one
  call is enough. `async for` never does this for you, which is why it is
  explicit.
- **`Seq.to_async()`** — bridges a sync chain into an async one:
  `Seq(urls).filter(is_valid).to_async().map_concurrent(fetch, limit=20)`.

### Fixed

- **The published wheel no longer fails to import in a clean environment.**
  `friendly_sequences` imported `TypeVarTuple` and `Unpack` from
  `typing_extensions` at runtime, but declared only `attrs` as a runtime
  dependency, so importing the wheel in an environment without
  `typing-extensions` raised `ImportError`. Migrating to PEP 695 syntax removed
  the import rather than adding a dependency. `attrs` remains the only runtime
  requirement.
- **`Seq` now validates its input element types.** Its converter was an
  untyped lambda, whose `Any` return suppressed type checking at construction:
  `Seq[int](["a", "b"])` passed silently, and `Seq((1, 2, 3))` inferred
  `Seq[Never]`, so `Seq((1, 2, 3)).map(lambda s: s.upper())` was not flagged.
  Both are now type errors. This is a type-checking change only — no runtime
  behaviour changed — but it may surface pre-existing mistakes in code that
  type-checked before.

### Changed

- Internals split into `_sync.py`, `_async.py` and `_typing.py`. `Seq`'s public
  import path is unchanged; `from friendly_sequences import Seq` still works.
- Generics migrated to PEP 695 syntax. The class type parameter remains an
  explicit covariant `TypeVar`, because PEP 695 has no syntax for declaring
  variance and inferring it would silently make `Seq` invariant.
