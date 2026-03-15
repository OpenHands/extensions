def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def find_longest(words: list[str]) -> str | None:
    """Find the longest word in a list."""
    if not words:
        return None
    return max(words, key=len)


class Calculator:
    def __init__(self, initial_value: float) -> None:
        self.value: float = initial_value

    def add(self, n: float) -> "Calculator":
        self.value += n
        return self

    def subtract(self, n: float) -> "Calculator":
        self.value -= n
        return self

    def get_value(self) -> float:
        return self.value
