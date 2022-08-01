import warnings
from typing import Callable, Union

import pystac

from pystac_client.errors import IgnoredResultWarning

Modifiable = Union[pystac.Collection, pystac.Item, pystac.ItemCollection, dict]


def no_modifier(x: Modifiable) -> None:
    """A default 'modifier' that does not modify the object."""
    pass


def call_modifier(modifier: Callable[[Modifiable], None], obj: Modifiable) -> None:
    """Calls the user's modifier and validates that the result is None."""
    result = modifier(obj)
    if result is not None and result is not obj:
        warnings.warn(
            f"modifier '{modifier}' returned a result that's being ignored. "
            "You should ensure that 'modifier' is operating in-place and use "
            "a function that returns 'None' or silence this warning.",
            IgnoredResultWarning,
        )
