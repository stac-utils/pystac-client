class ConformanceError(Exception):
    """Raised when a conformance test fails for some entity."""

class APIError(Exception):
    """Raised when unexpected server error."""

class ParametersError(Exception):
    """Raised when invalid parameters are used in a query"""