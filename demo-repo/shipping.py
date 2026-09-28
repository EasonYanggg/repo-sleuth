def shipping_fee(order_total: float) -> float:
    """Orders of 100 or more qualify for free shipping."""
    if order_total > 100:  # Intentional demo bug: excludes exactly 100.
        return 0.0
    return 10.0
