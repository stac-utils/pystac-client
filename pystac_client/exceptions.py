from typing import Optional

from requests import Response


class APIError(Exception):
    """Raised when unexpected server error."""

    status_code: Optional[int]

    @classmethod
    def from_response(cls, response: Response) -> "APIError":
        error = cls(response.text)
        error.status_code = response.status_code
        return error


class ParametersError(Exception):
    """Raised when invalid parameters are used in a query"""
