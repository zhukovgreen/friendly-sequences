# Friendly Sequences

Inspired by Scala Sequence class [1]. Good typing support.


## Examples

```python
from friendly_sequences import Seq


assert (
    Seq((1, 2))
    .zip(Seq((3, 4)))
    .flat_map(lambda x: x)
    .sort()
    .map(str)
    .to_tuple()
) == ("1", "2", "3", "4")
```

[1] https://alvinalexander.com/scala/seq-class-methods-examples-syntax/
