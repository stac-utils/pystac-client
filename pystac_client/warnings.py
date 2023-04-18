from contextlib import contextmanager
from typing import Iterator
import warnings


FALLBACK_MSG = "Falling back to pystac. This might be slow."


class PystacClientWarning(UserWarning):
    """Base warning class"""

    ...


class NoConformsTo(PystacClientWarning):
    """Inform user when client does not have "conformsTo" set"""

    ...


class DoesNotConformTo(PystacClientWarning):
    """Inform user when client does not conform to extension"""

    ...


class MissingLink(PystacClientWarning):
    """Inform user when link is properly implemented"""

    ...


class FallbackToPystac(PystacClientWarning):
    """Inform user when falling back to pystac implementation"""

    ...


@contextmanager
def strict() -> Iterator[None]:
    """Context manager for raising all pystac-client warnings as errors

    For more fine-grained control or to set filter warnings in the whole
    python session, use the ``warnings`` module directly.

    Examples:

    >>> import warnings
    >>> warnings.filterwarnings("error", category=FallbackToPystac)
    """

    warnings.filterwarnings("error", category=PystacClientWarning)
    try:
        yield
    finally:
        warnings.filterwarnings("default", category=PystacClientWarning)


@contextmanager
def ignore():  # type: ignore
    """Context manager for ignoring all pystac-client warnings

    For more fine-grained control or to set filter warnings in the whole
    python session, use the ``warnings`` module directly.

    Examples:

    >>> import warnings
    >>> warnings.filterwarnings("ignore", category=FallbackToPystac)
    """
    warnings.filterwarnings("ignore", category=PystacClientWarning)
    try:
        yield
    finally:
        warnings.filterwarnings("default", category=PystacClientWarning)
