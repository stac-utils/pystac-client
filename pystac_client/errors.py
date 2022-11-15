class ClientTypeError(Exception):
    """Raised when trying to open a Client on a non-catalog STAC Object."""

    pass


class IgnoredResultWarning(RuntimeWarning):
    """
    Warning raised when a 'modifier' callable returns a result.
    """
