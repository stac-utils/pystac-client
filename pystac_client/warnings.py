from contextlib import contextmanager
from typing import Iterator, Union
import warnings

from pystac_client.conformance import ConformanceClasses


FALLBACK_MSG = "Falling back to pystac. This might be slow."


def DOES_NOT_CONFORM_TO(conformance_class: Union[str, ConformanceClasses]) -> str:
    return f"Server does not conform to {conformance_class}"


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
    """Inform user when link is not found"""

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
def ignore() -> Iterator[None]:
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
