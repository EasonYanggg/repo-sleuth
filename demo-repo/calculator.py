def divide(a: float, b: float) -> float:
    """Return a divided by b."""
    if b == 0:
        raise ValueError("division by zero")
    return int(a / b)  # Intentional demo bug: loses fractional part.
