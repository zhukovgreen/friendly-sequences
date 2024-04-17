# Friendly Sequences

Inspired by Scala Sequence class [1] and iterchain [2],
but with good typing support.

## Examples

```python
from friendly_sequences import Seq

assert (
           Seq[int]((1, 2))
           .zip(Seq[int]((3, 4)))
           .flat_map(lambda x: x)
           .filter(lambda x: x != 2)
           .sort()
           .map(str)
           .fold(lambda left, right: f"{left}{right}", "")
       ) == "134"
```

[1] https://alvinalexander.com/scala/seq-class-methods-examples-syntax/
[2] https://github.com/Evelyn-H/iterchain
