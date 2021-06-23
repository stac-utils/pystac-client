class APIError(Exception):
    """Raised when unexpected server error."""


class ParametersError(Exception):
    """Raised when invalid parameters are used in a query"""
