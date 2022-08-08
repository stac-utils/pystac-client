import warnings
from typing import Callable, Optional, Union

import pystac

from pystac_client.errors import IgnoredResultWarning

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
