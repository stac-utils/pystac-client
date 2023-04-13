import warnings
from typing import Callable, Optional, Protocol, Union, Dict, Any
import pystac

from pystac_client.errors import IgnoredResultWarning
from pystac_client.exceptions import APIError
from pystac_client.conformance import ConformanceClasses
from pystac_client.stac_api_io import StacApiIO


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


class StacAPIProtocol(Protocol):
    _stac_io: Optional[StacApiIO]

    def get_self_href(self) -> str:
        ...


class QueryableMixin:
    def get_queryables(self: StacAPIProtocol) -> Dict[str, Any]:
        """Return all queryables.

        Output is a dictionary that can be used in ``jsonshema.validate``

        Return:
            Dict[str, Any]: Dictionary containing queryable fields
        """
        if self._stac_io is None:
            raise APIError("API access is not properly configured")

        self._stac_io.assert_conforms_to(ConformanceClasses.FILTER)

        self_href = self.get_self_href()
        if self_href is None:
            raise ValueError("Cannot build a queryable href without a self href")

        url = f"{self_href.rstrip('/')}/queryables"

        result = self._stac_io.read_json(url)
        if "properties" not in result:
            raise APIError("Invalid response from /queryables")

        return result
