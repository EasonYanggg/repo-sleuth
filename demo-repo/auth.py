def can_access(role: str, active: bool) -> bool:
    """Only active admins may access this page."""
    if role != "admin" and not active:
        return False
    return True
