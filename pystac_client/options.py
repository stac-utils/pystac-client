from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    Options = Literal[
        "enforce_conformance",
        "fallback_to_pystac",
        "on_fallback_to_pystac",

    ]

    class T_Options(TypedDict):
        enforce_conformance: bool
        fallback_to_pystac: bool
        on_fallback_to_pystac: Literal["ignore", "warn", "error"]

OPTIONS: T_Options = {
    "enforce_conformance": True,
    "fallback_to_pystac": True,
    "on_fallback_to_pystac": "ignore",
}

_ON_FALLBACK_TO_PYSTAC = frozenset(["ignore", "warn", "error"])


_VALIDATORS = {
    "enforce_conformance": lambda value: isinstance(value, bool),
    "fallback_to_pystac": lambda value: isinstance(value, bool),
    "on_fallback_to_pystac": _ON_FALLBACK_TO_PYSTAC.__contains__,
}


class set_options:
    """
    Set options for pystac-client in a controlled context.

    Parameters
    ----------
    enforce_conformance : bool, default: True
        Whether to enforce that conformance classes are properly set up.
    fallback_to_pystac : bool, default: True
        Whether to fall back to pystac implementation of methods if API
        implementation is not available.
    on_fallback_to_pystac : {"ignore", "warn", "error"}, default: "ignore
        How to inform user when falling back to pystac implementation

        * ``ignore`` : to silently allow
        * ``warn`` : to raise a warning
        * ``error`` : to raise an error

    Examples
    --------
    It is possible to use ``set_options`` either as a context manager:

    >>> with set_options(enforce_conformance=False):
    ...     Client.open(url)

    Or to set global options:

    >>> set_options(fallback_to_pystac=False)
    """

    def __init__(self, **kwargs):
        self.old = {}
        for k, v in kwargs.items():
            if k not in OPTIONS:
                raise ValueError(
                    f"argument name {k!r} is not in the set of valid options {set(OPTIONS)!r}"
                )
            if k in _VALIDATORS and not _VALIDATORS[k](v):
                if k == "on_fallback_to_pystac":
                    expected = f"Expected one of {_ON_FALLBACK_TO_PYSTAC!r}"
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


def get_options(*fields: str):
    """
    Get options for pystac-client

    See Also
    ----------
    set_options

    """
    return OPTIONS


# from dataclasses import dataclass, field


# @dataclass
# class Options:
#     """Options for pystac"""
#     enforce_conformance: bool = field(default=True)
#     fallback_to_pystac: bool = field(default=True)
#     on_fallback_to_pystac: Literal["ignore", "warn", "error"] = field(default="ignore")
