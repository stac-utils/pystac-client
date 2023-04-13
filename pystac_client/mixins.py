from typing import Optional, Protocol, Dict, Any, Union
import pystac
from pystac_client.exceptions import APIError
from pystac_client.conformance import ConformanceClasses
from pystac_client.stac_api_io import StacApiIO

QUERYABLES_REL = "http://www.opengis.net/def/rel/ogc/1.0/queryables"
QUERYABLES_ENDPOINT = "/queryables"


class StacAPIProtocol(Protocol):
    _stac_io: Optional[StacApiIO]

    def get_self_href(self) -> str:
        ...

    def get_single_link(
        self,
        rel: Optional[Union[str, pystac.RelType]] = None,
        media_type: Optional[Union[str, pystac.MediaType]] = None,
    ) -> Optional[pystac.Link]:
        ...


class QueryablesMixin:
    """Mixin for adding support for /queryables endpoint"""

    def get_queryables(self: StacAPIProtocol) -> Dict[str, Any]:
        """Return all queryables.

        Output is a dictionary that can be used in ``jsonshema.validate``

        Return:
            Dict[str, Any]: Dictionary containing queryable fields
        """
        if self._stac_io is None:
            raise APIError("API access is not properly configured")

        self._stac_io.assert_conforms_to(ConformanceClasses.FILTER)

        # The queryables link should be defined at the root, but if it is not
        # try to guess the url
        link = self.get_single_link(QUERYABLES_REL)
        if link is not None:
            url = link.href
        else:
            self_href = self.get_self_href()
            if self_href is None:
                raise ValueError("Cannot build a queryable href without a self href")
            url = f"{self_href.rstrip('/')}{QUERYABLES_ENDPOINT}"

        result = self._stac_io.read_json(url)
        if "properties" not in result:
            raise APIError(f"Invalid response from {QUERYABLES_ENDPOINT}")

        return result
