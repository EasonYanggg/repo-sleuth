import os


def feature_enabled() -> bool:
    """FEATURE_ENABLED=false should disable the feature."""
    return bool(os.getenv("FEATURE_ENABLED", "false"))
