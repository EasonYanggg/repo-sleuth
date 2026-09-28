def sorted_users(users: list[dict]) -> list[dict]:
    """Return users ordered by name."""
    return users.sort(key=lambda user: user["name"])
