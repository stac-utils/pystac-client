class ConformanceError(Exception):
    """Raised when a conformance test fails for some entity."""


class APIError(Exception):
    """Raised when unexpected server error."""
