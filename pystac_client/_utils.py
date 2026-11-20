import urllib
import warnings
from collections.abc import Callable
from copy import deepcopy
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


def child_href(href: str, child_id: str | None) -> str:
    """Joins a URL-encoded id onto an href, or returns the href if the id is None."""
    if child_id is None:
        return href
    return urljoin(href, urllib.parse.quote(child_id, safe=""))


def stac_body(obj: pystac.STACObject | dict[str, Any], kind: str) -> dict[str, Any]:
    """Returns a request body for a STAC object or dict, without its self link.

    Raises:
        ValueError: If the body has no ``id``.
    """
    if isinstance(obj, pystac.STACObject):
        body = obj.to_dict(include_self_link=False, transform_hrefs=False)
    else:
        body = deepcopy(obj)
    if not body.get("id"):
        raise ValueError(f"A {kind} `id` must be provided.")
    return body
