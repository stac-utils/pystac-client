import warnings
from typing import Any

import pystac

from pystac_client._utils import urljoin
from pystac_client.conformance import ConformanceClasses
from pystac_client.exceptions import APIError
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import DoesNotConformTo, MissingLink

QUERYABLES_REL = "http://www.opengis.net/def/rel/ogc/1.0/queryables"
QUERYABLES_ENDPOINT = "queryables"


class StacAPIObject(pystac.STACObject):
    _stac_io: StacApiIO | None

    def conforms_to(self, conformance_class: str | ConformanceClasses) -> bool:
        raise NotImplementedError


class BaseMixin(StacAPIObject):
    def _get_href(self, rel: str, link: pystac.Link | None, endpoint: str) -> str:
        if link and isinstance(link.href, str):
            href = link.absolute_href
        else:
            warnings.warn(MissingLink(rel, self.__class__.__name__), stacklevel=2)
            href = urljoin(self.self_href, endpoint)
        return href


class QueryablesMixin(BaseMixin):
    """Mixin for adding support for /queryables endpoint"""

    def get_queryables_from(self, url: str) -> dict[str, Any]:
        """Return all queryables.

        Output is a dictionary that can be used in ``jsonshema.validate``

        Args:
            url: a queryables url

        Return:
            Dict[str, Any]: Dictionary containing queryable fields
        """

        if self._stac_io is None:
            raise APIError("API access is not properly configured")

        result = self._stac_io.read_json(url)
        if "properties" not in result:
            raise APIError(
                f"Invalid response from {QUERYABLES_ENDPOINT}: "
                "expected 'properties' attribute"
            )

        return result

    def get_queryables(self) -> dict[str, Any]:
        url = self._get_queryables_href()
        return self.get_queryables_from(url)

    def _get_queryables_href(self) -> str:
        if not self.conforms_to(ConformanceClasses.FILTER):
            raise DoesNotConformTo(ConformanceClasses.FILTER.name)

        link = self.get_single_link(QUERYABLES_REL)
        href = self._get_href(QUERYABLES_REL, link, QUERYABLES_ENDPOINT)
        return href
