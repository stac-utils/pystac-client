from __future__ import annotations
from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    Options = Literal[
        "on_does_not_conform_to",
        "on_missing_link",
        "on_fallback_to_pystac",
    ]

    class T_Options(TypedDict):
        on_does_not_conform_to: Literal["ignore", "warn", "error"]
        on_missing_link: Literal["ignore", "warn", "error"]
        on_fallback_to_pystac: Literal["ignore", "warn", "error"]


OPTIONS: T_Options = {
    "on_does_not_conform_to": "warn",
    "on_missing_link": "ignore",
    "on_fallback_to_pystac": "ignore",
}

_ON_OPTIONS = frozenset(["ignore", "warn", "error"])


_VALIDATORS = {
    "on_does_not_conform_to": _ON_OPTIONS.__contains__,
    "on_missing_link": _ON_OPTIONS.__contains__,
    "on_fallback_to_pystac": _ON_OPTIONS.__contains__,
}


class set_options:
    """
    Set options for pystac-client in a controlled context.

    Parameters
    ----------
    on_does_not_conform_to : {"ignore", "warn", "error"}, default: "warn"
        How to inform user when client does not conform to extension

        * ``ignore`` : to silently allow
        * ``warn`` : to raise a warning
        * ``error`` : to raise an error

    on_missing_link : {"ignore", "warn", "error"}, default: "ignore"
        How to inform user when link is properly implemented

        * ``ignore`` : to silently allow
        * ``warn`` : to raise a warning
        * ``error`` : to raise an error

    on_fallback_to_pystac : {"ignore", "warn", "error"}, default: "ignore"
        How to inform user when falling back to pystac implementation

        * ``ignore`` : to silently allow
        * ``warn`` : to raise a warning
        * ``error`` : to raise an error

    Examples
    --------
    It is possible to use ``set_options`` either as a context manager:

    >>> with set_options(on_does_not_conform_to="ignore"):
    ...     Client.open(url)

    Or to set global options:

    >>> set_options(on_fallback_to_pystac="error")
    """

    def __init__(self, **kwargs):
        self.old = {}
        for k, v in kwargs.items():
            if k not in OPTIONS:
                raise ValueError(
                    f"argument name {k!r} is not in the set of valid options {set(OPTIONS)!r}"
                )
            if k in _VALIDATORS and not _VALIDATORS[k](v):
                expected = f"Expected one of {_ON_OPTIONS!r}"
                raise ValueError(
                    f"option {k!r} given an invalid value: {v!r}." + expected
                )
            self.old[k] = OPTIONS[k]
        self._apply_update(kwargs)

    def _apply_update(self, options_dict):
        OPTIONS.update(options_dict)

    def __enter__(self):
        return

    def __exit__(self, type, value, traceback):
        self._apply_update(self.old)


def get_options():
    """
    Get options for pystac-client

    See Also
    ----------
    set_options

    """
    return OPTIONS
