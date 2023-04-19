from typing import Optional, Dict, Any

import pystac

from pystac_client.exceptions import APIError
from pystac_client.conformance import ConformanceClasses
from pystac_client.stac_api_io import StacApiIO

QUERYABLES_REL = "http://www.opengis.net/def/rel/ogc/1.0/queryables"
QUERYABLES_ENDPOINT = "/queryables"


class StacAPIObject(pystac.STACObject):
    _stac_io: Optional[StacApiIO]


class QueryablesMixin(StacAPIObject):
    """Mixin for adding support for /queryables endpoint"""

    def get_queryables(self) -> Dict[str, Any]:
        """Return all queryables.

        Output is a dictionary that can be used in ``jsonshema.validate``

        Return:
            Dict[str, Any]: Dictionary containing queryable fields
        """
        if self._stac_io is None:
            raise APIError("API access is not properly configured")

        self._stac_io.assert_conforms_to(ConformanceClasses.FILTER)
        url = self._get_queryables_href()

        result = self._stac_io.read_json(url)
        if "properties" not in result:
            raise APIError(
                f"Invalid response from {QUERYABLES_ENDPOINT}: "
                "expected 'properties' attribute"
            )

        return result

    def _get_queryables_href(self) -> str:
        link = self.get_single_link(QUERYABLES_REL)
        if link is not None:
            url = link.href
        else:
            # The queryables link should be defined at the root, but if it is not
            # try to guess the url
            url = f"{self.self_href.rstrip('/')}{QUERYABLES_ENDPOINT}"
        return url
