import urllib
import warnings
from collections.abc import Callable
from typing import Any, Union

import pystac

from pystac_client.errors import IgnoredResultWarning

Modifiable = Union[
    pystac.Collection, pystac.Item, pystac.ItemCollection, dict[Any, Any]
]


def call_modifier(
    modifier: Callable[[Modifiable], None] | None, obj: Modifiable
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


def urljoin(href: str, name: str) -> str:
    """Joins a path onto an existing href, respecting query strings, etc."""
    url = urllib.parse.urlparse(href)
    path = url.path
    if not path.endswith("/"):
        path += "/"
    return urllib.parse.urlunparse(url._replace(path=path + name))
