def total_with_tax(subtotal: float, rate: float) -> float:
    """rate is a percentage, e.g. 8 means 8 percent."""
    return subtotal * (1 + rate)
