from contextlib import contextmanager
import warnings


FALLBACK_MSG = "Falling back to pystac. This might be slow."


class PystacClientWarning(UserWarning):
    """Base warning class"""

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
def strict():  # type: ignore
    warnings.filterwarnings("error", category=PystacClientWarning)
    try:
        yield
    finally:
        warnings.resetwarnings()


@contextmanager
def lax():  # type: ignore
    warnings.filterwarnings("ignore", category=PystacClientWarning)
    try:
        yield
    finally:
        warnings.resetwarnings()
