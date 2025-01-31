import warnings
from collections.abc import Iterator
from contextlib import contextmanager


class PystacClientWarning(UserWarning):
    """Base warning class"""

    ...


class NoConformsTo(PystacClientWarning):
    """Inform user when client does not have "conformsTo" set"""

    def __str__(self) -> str:
        return "Server does not advertise any conformance classes."


class DoesNotConformTo(PystacClientWarning):
    """Inform user when client does not conform to extension"""

    def __str__(self) -> str:
        return "Server does not conform to {}".format(", ".join(self.args))


class MissingLink(PystacClientWarning):
    """Inform user when link is not found"""

    def __str__(self) -> str:
        return "No link with rel='{}' could be found on this {}.".format(*self.args)


class FallbackToPystac(PystacClientWarning):
    """Inform user when falling back to pystac implementation"""

    def __str__(self) -> str:
        return "Falling back to pystac. This might be slow."


@contextmanager
def strict() -> Iterator[None]:
    """Context manager for raising all pystac-client warnings as errors

    For more fine-grained control or to filter warnings in the whole
    python session, use the :py:mod:`warnings` module directly.

    Examples:

    >>> from pystac_client import Client
    >>> from pystac_client.warnings import strict
    >>> with strict():
    ...     Client.open("https://perfect-api.test")

    For finer-grained control:

    >>> import warnings
    >>> from pystac_client import Client
    >>> from pystac_client.warnings import MissingLink
    >>> warnings.filterwarnings("error", category=FallbackToPystac)
    >>> Client.open("https://imperfect-api.test")
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

    >>> from pystac_client import Client
    >>> from pystac_client.warnings import ignore
    >>> with ignore():
    ...     Client.open("https://perfect-api.test")

    For finer-grained control:

    >>> import warnings
    >>> from pystac_client import Client
    >>> from pystac_client.warnings import MissingLink
    >>> warnings.filterwarnings("ignore", category=MissingLink)
    >>> Client.open("https://imperfect-api.test")
    """
    warnings.filterwarnings("ignore", category=PystacClientWarning)
    try:
        yield
    finally:
        warnings.filterwarnings("default", category=PystacClientWarning)
