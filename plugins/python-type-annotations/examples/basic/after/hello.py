def greet(name):
    """Return a greeting message."""
    return f"Hello, {name}!"


def add(a, b):
    """Add two numbers."""
    return a + b


def find_longest(words):
    """Find the longest word in a list."""
    if not words:
        return None
    return max(words, key=len)


class Calculator:
    def __init__(self, initial_value):
        self.value = initial_value

    def add(self, n):
        self.value += n
        return self

    def subtract(self, n):
        self.value -= n
        return self

    def get_value(self):
        return self.value
