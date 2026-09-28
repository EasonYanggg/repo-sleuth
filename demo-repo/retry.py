def attempts_allowed(max_attempts: int) -> int:
    """Return the number of attempts made before stopping."""
    attempts = 0
    while attempts <= max_attempts:
        attempts += 1
    return attempts
