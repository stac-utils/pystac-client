import warnings
from typing import Callable, Optional, Union, Literal, cast

import pystac

from pystac_client.errors import IgnoredResultWarning
from pystac_client.options import get_options, T_Keys

Modifiable = Union[pystac.Collection, pystac.Item, pystac.ItemCollection, dict]


def call_modifier(
    modifier: Optional[Callable[[Modifiable], None]], obj: Modifiable
) -> None:
    """Calls the user's modifier and validates that the result is None."""
    if modifier is None:
        return None

    result = modifier(obj)
    if result is not None and result is not obj:
        warnings.warn(
            f"modifier '{modifier}' returned a result that's being ignored. "
            "You should ensure that 'modifier' is operating in-place and use "
            "a function that returns 'None' or silence this warning.",
            IgnoredResultWarning,
        )


def respond(
    event: Literal["does_not_conform_to", "missing_link", "fallback_to_pystac"],
    msg: str,
) -> None:
    """Response to event based on user-configured options"""
    on_event = get_options()[cast(T_Keys, f"on_{event}")]
    if on_event == "ignore":
        pass
    elif on_event == "warn":
        warnings.warn(msg, UserWarning)
    elif on_event == "error":
        raise NotImplementedError(msg)
