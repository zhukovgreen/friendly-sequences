from typing import TypeGuard

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
    ).to_tuple() == (2, 3, 4, 5)


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
    ).to_tuple() == ("a1", "b2")


async def test_starmap_with_async_callable():
    async def combine(a: str, b: int) -> str:
        return a + str(b)

    assert await AsyncSeq((("a", 1), ("b", 2))).starmap(
        combine
    ).to_tuple() == ("a1", "b2")


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
    ).flatten().to_tuple() == (1, 2, 3, 4)


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
        await AsyncSeq((1, 2)).zip(
            AsyncSeq((3, 4)),
            AsyncSeq((5, 6, 7)),
            strict=True,
        ).to_tuple()


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
