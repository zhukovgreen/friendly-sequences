from typing import TypeGuard

from friendly_sequences import Seq


def test_usage():
    def add_one(i: int) -> int:
        return i + 1

    assert Seq((1, 2, 3)).map(add_one).sum() == 9
    assert Seq((1,)).sum() == 1
    assert next(Seq((1, 2)).take(1)) == 1
    assert (
        Seq(
            (
                (1, 2),
                (3, 4),
            )
        )
        .flat_map(add_one)
        .sum()
        == 14
    )
    assert Seq("cba").sort().join() == "abc"
    assert (
        Seq((1, 2))
        .zip(Seq((3, 4)))
        .flat_map(lambda x: x)
        .sort()
        .map(str)
        .reduce(lambda left, right: left + right)
    ) == "1234"

    assert Seq((1, 2, 3)).map(lambda x: x // 2 == 0).all() is False
    assert Seq((2, 4, 6)).map(lambda x: x // 2 == 0).all() is False
    assert Seq((1, 2, 3)).map(lambda x: x // 2 == 0).any() is True


def test_chaining():
    def filter_expr(i: int) -> TypeGuard[int]:
        return i != 2

    assert (
        Seq[int]((1, 2))
        .zip(Seq[int]((3, 4)))
        .flat_map(lambda x: x + 1)
        .filter(filter_expr)
        .sort(reverse=True)
        .map(str)
        .fold(lambda left, right: f"{left}{right}", "")
    ) == "543"


def test_flatten():
    assert Seq(((1, 2), (3, 4))).flatten().to_tuple() == (1, 2, 3, 4)


def test_starmap():
    def foo(a: str, b: int) -> str:
        return a + str(b)

    assert Seq[tuple[str, int]]((("a", 1), ("b", 2))).starmap(
        foo
    ).to_tuple() == ("a1", "b2")


def test_flatmap():
    def foo(s: str) -> str:
        return f"{s}!"

    assert Seq[tuple[str]]((("a",), ("b",))).flat_map(foo).to_tuple() == (
        "a!",
        "b!",
    )
    assert Seq[Seq[str]](Seq((("a",), ("b",)))).flat_map(foo).to_tuple() == (
        "a!",
        "b!",
    )


def test_exhaust():
    class Switch:
        on: bool = False

        def turn_on(self):
            self.on = True

    switches = 3 * (Switch(),)

    # define pipeline and ensure it is not executed
    pipeline = Seq[Switch](switches).map(lambda switch: switch.turn_on())

    assert Seq[Switch](switches).map(
        lambda switch: switch.on is True
    ).to_tuple() == 3 * (False,)

    # exhaust the iterator and ensure it returns None
    assert pipeline.exhaust() is None  # type: ignore
    assert Seq[Switch](switches).map(
        lambda switch: switch.on is True
    ).to_tuple() == 3 * (True,)


def test_accessing_methods():
    assert Seq((1,)).head() == 1
    assert Seq((1,)).to_tuple() == (1,)
    assert Seq((1,)).to_list() == [1]
    assert Seq[int]((1, 2)).zip(Seq[int]((1, 2))).to_dict() == {1: 1, 2: 2}
