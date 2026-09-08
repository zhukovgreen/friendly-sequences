import asyncio

from typing import TYPE_CHECKING, TypeGuard

import pytest

from friendly_sequences import AsyncSeq, Seq


async def add_one(i: int) -> int:
    return i + 1


def add_one_sync(i: int) -> int:
    return i + 1


async def gen_range(*values: int):
    for value in values:
        yield value


async def test_map_with_sync_callable():
    assert await AsyncSeq((1, 2, 3)).map(add_one_sync).to_tuple() == (
        2,
        3,
        4,
    )


async def test_map_with_async_callable():
    assert await AsyncSeq((1, 2, 3)).map(add_one).to_tuple() == (2, 3, 4)


async def test_flat_map_with_sync_callable_over_sync_iterables():
    assert await AsyncSeq(((1, 2), (3, 4))).flat_map(
        add_one_sync
    ).to_tuple() == (
        2,
        3,
        4,
        5,
    )


async def test_flat_map_with_async_callable_over_sync_iterables():
    assert await AsyncSeq(((1, 2), (3, 4))).flat_map(add_one).to_tuple() == (
        2,
        3,
        4,
        5,
    )


async def test_flat_map_with_sync_callable_over_async_iterables():
    assert await AsyncSeq((gen_range(1, 2), gen_range(3, 4))).flat_map(
        add_one_sync
    ).to_tuple() == (2, 3, 4, 5)


async def test_flat_map_with_async_callable_over_async_iterables():
    assert await AsyncSeq((gen_range(1, 2), gen_range(3, 4))).flat_map(
        add_one
    ).to_tuple() == (2, 3, 4, 5)


async def test_starmap_with_sync_callable():
    def combine(a: str, b: int) -> str:
        return a + str(b)

    assert await AsyncSeq((("a", 1), ("b", 2))).starmap(
        combine
    ).to_tuple() == (
        "a1",
        "b2",
    )


async def test_starmap_with_async_callable():
    async def combine(a: str, b: int) -> str:
        return a + str(b)

    assert await AsyncSeq((("a", 1), ("b", 2))).starmap(
        combine
    ).to_tuple() == (
        "a1",
        "b2",
    )


async def test_flatten_over_sync_iterables():
    assert await AsyncSeq(((1, 2), (3, 4))).flatten().to_tuple() == (
        1,
        2,
        3,
        4,
    )


async def test_flatten_over_async_iterables():
    assert await AsyncSeq(
        (gen_range(1, 2), gen_range(3, 4))
    ).flatten().to_tuple() == (
        1,
        2,
        3,
        4,
    )


async def test_filter_with_sync_typeguard():
    def is_int(value: object) -> TypeGuard[int]:
        return isinstance(value, int)

    assert await AsyncSeq((1, 2, 3)).filter(is_int).to_tuple() == (1, 2, 3)


async def test_filter_with_sync_bool_callable():
    assert await AsyncSeq((1, 2, 3)).filter(lambda i: i != 2).to_tuple() == (
        1,
        3,
    )


async def test_filter_with_async_bool_callable():
    async def is_odd(i: int) -> bool:
        return i % 2 == 1

    assert await AsyncSeq((1, 2, 3)).filter(is_odd).to_tuple() == (1, 3)


async def test_fold_with_sync_callable():
    assert (
        await AsyncSeq((1, 2, 3)).fold(lambda left, right: left + right, 0)
    ) == 6


async def test_fold_with_async_callable():
    async def combine(left: int, right: int) -> int:
        return left + right

    assert await AsyncSeq((1, 2, 3)).fold(combine, 0) == 6


async def test_reduce_with_sync_callable():
    assert (
        await AsyncSeq((1, 2, 3)).reduce(lambda left, right: left + right)
    ) == 6


async def test_reduce_with_async_callable():
    async def combine(left: int, right: int) -> int:
        return left + right

    assert await AsyncSeq((1, 2, 3)).reduce(combine) == 6


async def test_reduce_raises_on_empty_sequence():
    with pytest.raises(TypeError, match="reduce\\(\\) of empty iterable"):
        await AsyncSeq[int](()).reduce(lambda left, right: left + right)


async def test_take():
    assert await AsyncSeq((1, 2, 3)).take(2).to_tuple() == (1, 2)


async def test_take_more_than_available():
    assert await AsyncSeq((1,)).take(2).to_tuple() == (1,)


async def test_sort_drains_lazily_and_still_chains():
    drained = False

    async def source():
        nonlocal drained
        for value in (3, 1, 2):
            yield value
        drained = True

    pipeline = AsyncSeq(source()).sort()
    assert drained is False

    assert await pipeline.map(str).to_tuple() == ("1", "2", "3")
    assert drained is True


async def test_sort_reverse():
    assert await AsyncSeq((3, 1, 2)).sort(reverse=True).to_tuple() == (
        3,
        2,
        1,
    )


async def test_zip():
    assert await AsyncSeq((1, 2)).zip(AsyncSeq((3, 4))).to_tuple() == (
        (1, 3),
        (2, 4),
    )


async def test_zip_strict_raises_when_left_longer():
    with pytest.raises(ValueError, match=r"zip\(\) argument 2 is shorter"):
        await AsyncSeq((1, 2, 3)).zip(AsyncSeq((1, 2)), strict=True).to_tuple()


async def test_zip_strict_raises_when_right_longer():
    with pytest.raises(ValueError, match=r"zip\(\) argument 2 is longer"):
        await AsyncSeq((1, 2)).zip(AsyncSeq((1, 2, 3)), strict=True).to_tuple()


async def test_zip_strict_raises_when_third_argument_is_longer():
    with pytest.raises(ValueError, match=r"zip\(\) argument 3 is longer"):
        await (
            AsyncSeq((1, 2))
            .zip(
                AsyncSeq((3, 4)),
                AsyncSeq((5, 6, 7)),
                strict=True,
            )
            .to_tuple()
        )


async def test_sum():
    assert await AsyncSeq((1, 2, 3)).sum() == 6


async def test_to_tuple():
    assert await AsyncSeq((1, 2, 3)).to_tuple() == (1, 2, 3)


async def test_to_list():
    assert await AsyncSeq((1, 2, 3)).to_list() == [1, 2, 3]


async def test_to_dict():
    assert await AsyncSeq(((1, "a"), (2, "b"))).to_dict() == {
        1: "a",
        2: "b",
    }


async def test_exhaust():
    class Switch:
        on: bool = False

        def turn_on(self) -> None:
            self.on = True

    switches = 3 * (Switch(),)

    pipeline = AsyncSeq(switches).map(lambda switch: switch.turn_on())

    assert await AsyncSeq(switches).map(
        lambda switch: switch.on is True
    ).to_tuple() == 3 * (False,)

    await pipeline.exhaust()
    assert await AsyncSeq(switches).map(
        lambda switch: switch.on is True
    ).to_tuple() == 3 * (True,)


async def test_head():
    assert await AsyncSeq((1, 2, 3)).head() == 1


async def test_join():
    assert await AsyncSeq("cba").sort().join() == "abc"


async def test_all():
    assert await AsyncSeq((1, 2, 3)).map(lambda x: x // 2 == 0).all() is (
        False
    )
    assert await AsyncSeq((2, 4, 6)).map(lambda x: x // 2 == 0).all() is (
        False
    )


async def test_all_true():
    assert await AsyncSeq((1, 1, 1)).all() is True


async def test_any():
    assert await AsyncSeq((1, 2, 3)).map(lambda x: x // 2 == 0).any() is (True)


async def test_any_false():
    assert await AsyncSeq((0, 0, 0)).any() is False


async def test_chaining():
    def filter_expr(i: int) -> TypeGuard[int]:
        return i != 2

    assert (
        await AsyncSeq[int]((1, 2))
        .zip(AsyncSeq[int]((3, 4)))
        .flat_map(lambda x: x + 1)
        .filter(filter_expr)
        .sort(reverse=True)
        .map(str)
        .fold(lambda left, right: f"{left}{right}", "")
    ) == "543"


async def test_converter_accepts_sync_iterable():
    assert await AsyncSeq((1, 2, 3)).to_tuple() == (1, 2, 3)


async def test_converter_accepts_async_generator():
    assert await AsyncSeq(gen_range(1, 2, 3)).to_tuple() == (1, 2, 3)


async def test_converter_accepts_seq():
    assert await AsyncSeq(Seq((1, 2, 3))).to_tuple() == (1, 2, 3)


async def test_laziness():
    class Switch:
        on: bool = False

        def turn_on(self) -> None:
            self.on = True

    switches = 3 * (Switch(),)

    pipeline = AsyncSeq(switches).map(lambda switch: switch.turn_on())

    assert all(switch.on is False for switch in switches)
    await pipeline.exhaust()
    assert all(switch.on is True for switch in switches)


async def test_aclose_propagates_to_upstream_source():
    closed_count = 0

    async def source():
        nonlocal closed_count
        try:
            yield 1
            yield 2
        finally:
            closed_count += 1

    seq = AsyncSeq(source()).map(add_one_sync)

    assert await seq.__anext__() == 2
    assert closed_count == 0

    await seq.aclose()
    assert closed_count == 1


async def test_map_concurrent_with_sync_callable():
    assert await AsyncSeq((1, 2, 3)).map_concurrent(
        add_one_sync
    ).to_tuple() == (
        2,
        3,
        4,
    )


async def test_map_concurrent_with_async_callable():
    assert await AsyncSeq((1, 2, 3)).map_concurrent(add_one).to_tuple() == (
        2,
        3,
        4,
    )


async def test_map_unordered_with_sync_callable():
    assert set(
        await AsyncSeq((1, 2, 3)).map_unordered(add_one_sync).to_tuple()
    ) == {
        2,
        3,
        4,
    }


async def test_map_unordered_with_async_callable():
    assert set(
        await AsyncSeq((1, 2, 3)).map_unordered(add_one).to_tuple()
    ) == {2, 3, 4}


async def test_map_concurrent_preserves_input_order_under_jitter():
    delays = (0.12, 0.02, 0.07)

    async def mapper(index: int) -> int:
        await asyncio.sleep(delays[index])
        return index

    assert await AsyncSeq((0, 1, 2)).map_concurrent(
        mapper, limit=3
    ).to_tuple() == (
        0,
        1,
        2,
    )


async def test_map_unordered_yields_in_completion_order():
    delays = (0.12, 0.02, 0.07)

    async def mapper(index: int) -> int:
        await asyncio.sleep(delays[index])
        return index

    assert await AsyncSeq((0, 1, 2)).map_unordered(
        mapper, limit=3
    ).to_tuple() == (
        1,
        2,
        0,
    )


async def test_map_concurrent_respects_limit():
    in_flight = 0
    peak_in_flight = 0

    async def mapper(item: int) -> int:
        nonlocal in_flight, peak_in_flight
        in_flight += 1
        peak_in_flight = max(peak_in_flight, in_flight)
        try:
            await asyncio.sleep(0.02)
            return item
        finally:
            in_flight -= 1

    result = (
        await AsyncSeq(range(10)).map_concurrent(mapper, limit=3).to_tuple()
    )

    assert result == tuple(range(10))
    assert peak_in_flight <= 3
    assert peak_in_flight >= 2


async def test_map_concurrent_leaves_no_tasks_after_early_exit():
    async def mapper(item: int) -> int:
        await asyncio.sleep(0.05)
        return item

    result = (
        await AsyncSeq(range(5))
        .map_concurrent(mapper, limit=5)
        .take(1)
        .to_tuple()
    )

    assert result == (0,)
    remaining = asyncio.all_tasks() - {asyncio.current_task()}
    assert remaining == set()


async def test_map_unordered_leaves_no_tasks_after_early_exit():
    async def mapper(item: int) -> int:
        if item == 0:
            return item
        await asyncio.sleep(10)
        return item

    result = (
        await AsyncSeq(range(5))
        .map_unordered(mapper, limit=5)
        .take(1)
        .to_tuple()
    )

    assert result == (0,)
    remaining = asyncio.all_tasks() - {asyncio.current_task()}
    assert remaining == set()


async def test_aclose_cancels_in_flight_map_concurrent_work():
    finalized = 0

    async def mapper(item: int) -> int:
        nonlocal finalized
        try:
            if item == 0:
                return item
            await asyncio.sleep(10)
            return item
        finally:
            finalized += 1

    seq = AsyncSeq(range(5)).map_concurrent(mapper, limit=5)

    assert await seq.__anext__() == 0
    await seq.aclose()

    assert finalized == 5
    remaining = asyncio.all_tasks() - {asyncio.current_task()}
    assert remaining == set()


async def test_aclose_genuinely_cancels_slow_map_concurrent_work():
    cancelled = 0

    async def work(item: int) -> int:
        nonlocal cancelled
        try:
            await asyncio.sleep(0.001 if item == 0 else 1.0)
        except asyncio.CancelledError:
            cancelled += 1
            raise
        else:
            return item

    seq = AsyncSeq(range(5)).map_concurrent(work, limit=5)

    assert await seq.__anext__() == 0

    loop = asyncio.get_running_loop()
    started_at = loop.time()
    await seq.aclose()
    elapsed = loop.time() - started_at

    assert cancelled > 0
    assert elapsed < 0.5


async def test_chunked_exact_multiple():
    result = await AsyncSeq(range(6)).chunked(2).to_list()

    assert result == [(0, 1), (2, 3), (4, 5)]
    assert all(isinstance(chunk, tuple) for chunk in result)


async def test_chunked_yields_short_final_chunk():
    result = await AsyncSeq(range(5)).chunked(2).to_list()

    assert result == [(0, 1), (2, 3), (4,)]
    assert all(isinstance(chunk, tuple) for chunk in result)


async def test_throttle_enforces_minimum_interval():
    loop = asyncio.get_running_loop()
    start = loop.time()

    result = await AsyncSeq(range(4)).throttle(per_second=20).to_list()

    elapsed = loop.time() - start
    assert result == [0, 1, 2, 3]
    assert elapsed >= 0.1


async def test_timeout_total_fires():
    async def slow_source():
        for value in range(5):
            await asyncio.sleep(0.05)
            yield value

    with pytest.raises(TimeoutError):
        await AsyncSeq(slow_source()).timeout(total=0.02).to_list()


async def test_timeout_total_does_not_fire():
    assert await AsyncSeq(range(3)).timeout(total=5).to_list() == [0, 1, 2]


async def test_timeout_per_item_fires():
    async def slow_source():
        yield 1
        await asyncio.sleep(0.2)
        yield 2

    with pytest.raises(TimeoutError):
        await AsyncSeq(slow_source()).timeout(per_item=0.02).to_list()


async def test_timeout_per_item_does_not_fire():
    assert await AsyncSeq(range(3)).timeout(per_item=5).to_list() == [
        0,
        1,
        2,
    ]


async def test_to_async_returns_async_seq_with_same_elements():
    assert await Seq((1, 2, 3)).to_async().to_tuple() == (1, 2, 3)


async def test_to_async_bridges_full_chain():
    def is_even(i: int) -> bool:
        return i % 2 == 0

    assert await Seq(range(5)).filter(is_even).to_async().map_concurrent(
        add_one
    ).to_list() == [1, 3, 5]


async def test_map_concurrent_propagates_error_and_drains_tasks():
    started = 0
    finalized = 0

    async def mapper(item: int) -> int:
        nonlocal started, finalized
        started += 1
        try:
            if item == 2:
                raise ValueError("boom")
            await asyncio.sleep(0.05)
            return item
        finally:
            finalized += 1

    with pytest.raises(ValueError, match="boom"):
        await AsyncSeq(range(5)).map_concurrent(mapper, limit=5).to_list()

    assert started == finalized
    remaining = asyncio.all_tasks() - {asyncio.current_task()}
    assert remaining == set()


async def test_map_unordered_propagates_error_and_drains_tasks():
    started = 0
    finalized = 0

    async def mapper(item: int) -> int:
        nonlocal started, finalized
        started += 1
        try:
            if item == 2:
                raise ValueError("boom")
            await asyncio.sleep(0.05)
            return item
        finally:
            finalized += 1

    with pytest.raises(ValueError, match="boom"):
        await AsyncSeq(range(5)).map_unordered(mapper, limit=5).to_list()

    assert started == finalized
    remaining = asyncio.all_tasks() - {asyncio.current_task()}
    assert remaining == set()


async def test_map_unordered_respects_limit():
    in_flight = 0
    peak_in_flight = 0

    async def mapper(item: int) -> int:
        nonlocal in_flight, peak_in_flight
        in_flight += 1
        peak_in_flight = max(peak_in_flight, in_flight)
        try:
            await asyncio.sleep(0.02)
            return item
        finally:
            in_flight -= 1

    result = (
        await AsyncSeq(range(10)).map_unordered(mapper, limit=3).to_tuple()
    )

    assert set(result) == set(range(10))
    assert peak_in_flight <= 3
    assert peak_in_flight >= 2


async def test_aclose_cancels_in_flight_map_unordered_work():
    finalized = 0

    async def mapper(item: int) -> int:
        nonlocal finalized
        try:
            if item == 0:
                return item
            await asyncio.sleep(10)
            return item
        finally:
            finalized += 1

    seq = AsyncSeq(range(5)).map_unordered(mapper, limit=5)

    assert await seq.__anext__() == 0
    await seq.aclose()

    assert finalized == 5
    remaining = asyncio.all_tasks() - {asyncio.current_task()}
    assert remaining == set()


async def test_aclose_genuinely_cancels_slow_map_unordered_work():
    cancelled = 0

    async def work(item: int) -> int:
        nonlocal cancelled
        try:
            await asyncio.sleep(0.001 if item == 0 else 1.0)
        except asyncio.CancelledError:
            cancelled += 1
            raise
        else:
            return item

    seq = AsyncSeq(range(5)).map_unordered(work, limit=5)

    assert await seq.__anext__() == 0

    loop = asyncio.get_running_loop()
    started_at = loop.time()
    await seq.aclose()
    elapsed = loop.time() - started_at

    assert cancelled > 0
    assert elapsed < 0.5


async def test_map_concurrent_over_empty_source():
    assert await AsyncSeq[int](()).map_concurrent(add_one).to_tuple() == ()


async def test_map_unordered_over_empty_source():
    assert await AsyncSeq[int](()).map_unordered(add_one).to_tuple() == ()


async def test_map_concurrent_limit_larger_than_number_of_items():
    assert await AsyncSeq((1, 2, 3)).map_concurrent(
        add_one, limit=100
    ).to_tuple() == (2, 3, 4)


async def test_map_unordered_limit_larger_than_number_of_items():
    assert set(
        await AsyncSeq((1, 2, 3)).map_unordered(add_one, limit=100).to_tuple()
    ) == {2, 3, 4}


async def test_map_concurrent_streams_a_bounded_window_of_the_source():
    pulled = 0

    async def counting_source():
        nonlocal pulled
        for i in range(1000):
            pulled += 1
            yield i

    async def slow(item: int) -> int:
        await asyncio.sleep(0.01)
        return item

    seq = AsyncSeq(counting_source()).map_concurrent(slow, limit=5)
    try:
        assert await seq.__anext__() == 0
    finally:
        await seq.aclose()

    assert pulled <= 10


async def test_map_unordered_streams_a_bounded_window_of_the_source():
    pulled = 0

    async def counting_source():
        nonlocal pulled
        for i in range(1000):
            pulled += 1
            yield i

    async def slow(item: int) -> int:
        await asyncio.sleep(0.01)
        return item

    seq = AsyncSeq(counting_source()).map_unordered(slow, limit=5)
    try:
        await seq.__anext__()
    finally:
        await seq.aclose()

    assert pulled <= 10


async def test_map_concurrent_limit_one_is_strictly_sequential():
    in_flight = 0
    peak_in_flight = 0

    async def mapper(item: int) -> int:
        nonlocal in_flight, peak_in_flight
        in_flight += 1
        peak_in_flight = max(peak_in_flight, in_flight)
        try:
            await asyncio.sleep(0.01)
            return item
        finally:
            in_flight -= 1

    result = (
        await AsyncSeq(range(5)).map_concurrent(mapper, limit=1).to_tuple()
    )

    assert result == tuple(range(5))
    assert peak_in_flight == 1


async def test_integration_sync_to_async_bridge_under_concurrency():
    def is_even(i: int) -> bool:
        return i % 2 == 0

    async def double(i: int) -> int:
        await asyncio.sleep(0.01)
        return i * 2

    result = await (
        Seq(range(10))
        .filter(is_even)
        .to_async()
        .map_concurrent(double, limit=3)
        .chunked(2)
        .to_list()
    )

    assert result == [(0, 4), (8, 12), (16,)]
    assert all(isinstance(chunk, tuple) for chunk in result)


async def test_integration_sort_feeds_map_concurrent():
    drained = False

    async def source():
        nonlocal drained
        for value in (3, 1, 2):
            yield value
        drained = True

    async def double(i: int) -> int:
        return i * 2

    pipeline = AsyncSeq(source()).sort().map_concurrent(double, limit=2)
    assert drained is False

    assert await pipeline.to_tuple() == (2, 4, 6)
    assert drained is True


async def test_integration_early_exit_through_full_pipeline_leaves_no_tasks():
    async def slow_double(i: int) -> int:
        await asyncio.sleep(0.05)
        return i * 2

    result = await (
        AsyncSeq(range(1000))
        .filter(lambda i: i % 2 == 0)
        .map_concurrent(slow_double, limit=10)
        .chunked(3)
        .take(1)
        .to_tuple()
    )

    assert result == ((0, 4, 8),)
    remaining = asyncio.all_tasks() - {asyncio.current_task()}
    assert remaining == set()


if TYPE_CHECKING:
    reveal_type(Seq[int]((1, 2)).to_async())  # noqa: F821
