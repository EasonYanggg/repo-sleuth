def page(items: list, start: int, size: int) -> list:
    """Return exactly size items starting at start."""
    return items[start:start + size - 1]
