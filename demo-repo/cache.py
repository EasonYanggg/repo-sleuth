def add_tag(tag: str, tags: list[str] = []) -> list[str]:
    """Return the tags for this call only."""
    tags.append(tag)
    return tags
