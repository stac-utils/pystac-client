from typing import Optional, Dict, Any

import pystac

from pystac_client.exceptions import APIError
from pystac_client.conformance import ConformanceClasses
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import DoesNotConformTo

QUERYABLES_REL = "http://www.opengis.net/def/rel/ogc/1.0/queryables"
QUERYABLES_ENDPOINT = "queryables"


class StacAPIObject(pystac.STACObject):
    _stac_io: Optional[StacApiIO]

    def conforms_to(self, conformance_class: ConformanceClasses) -> bool:
        raise NotImplementedError


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

        if not self.conforms_to(ConformanceClasses.FILTER):
            raise DoesNotConformTo(ConformanceClasses.FILTER.name)

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
        href = StacApiIO._get_href(self, QUERYABLES_REL, link, QUERYABLES_ENDPOINT)
        return href
