from copy import deepcopy
import json
import logging
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    TYPE_CHECKING,
    Union,
)
from urllib.parse import urlparse
from requests import Request, Session

import pystac
from pystac.link import Link
from pystac.serialization import (
    merge_common_properties,
    identify_stac_object_type,
    identify_stac_object,
    migrate_to_latest,
)
from pystac.stac_io import DefaultStacIO

import pystac_client
from .exceptions import APIError
from .conformance import ConformanceClasses, CONFORMANCE_URIS

if TYPE_CHECKING:
    from pystac.stac_object import STACObject as STACObject_Type
    from pystac.catalog import Catalog as Catalog_Type

logger = logging.getLogger(__name__)


class StacApiIO(DefaultStacIO):
    def __init__(self, headers: Optional[Dict] = None, conformance: Optional[List[str]] = None):
        """Initialize class for API IO

        Args:
            headers : Optional dictionary of headers to include in all requests

        Returns:
            StacApiIO : StacApiIO instance
        """
        # TODO - this should super() to parent class
        self.session = Session()
        self.session.headers.update(headers or {})

        self._conformance = conformance

    def read_text(self,
                  source: Union[str, Link],
                  *args: Any,
                  parameters: Optional[dict] = {},
                  **kwargs: Any) -> str:
        """Overwrites the default method for reading text from a URL or file to allow :class:`urllib.request.Request`
        instances as input. This method also raises any :exc:`urllib.error.HTTPError` exceptions rather than catching
        them to allow us to handle different response status codes as needed."""
        if isinstance(source, str):
            href = source
            if bool(urlparse(href).scheme):
                return self.request(href, *args, parameters=parameters, **kwargs)
            else:
                with open(href) as f:
                    href_contents = f.read()
                return href_contents
        elif isinstance(source, Link):
            link = source.to_dict()
            href = link['href']
            # get headers and body from Link and add to request from simple stac resolver
            merge = bool(link.get('merge', False))

            # If the link object includes a "method" property, use that. If not fall back to 'GET'.
            method = link.get('method', 'GET')
            # If the link object includes a "headers" property, use that and respect the "merge" property.
            headers = link.get('headers', None)

            # If "POST" use the body object that and respect the "merge" property.
            link_body = link.get('body', {})
            if method == 'POST':
                parameters = {**parameters, **link_body} if merge else link_body
            else:
                # parameters are already in the link href
                parameters = {}
            return self.request(href, *args, method=method, headers=headers, parameters=parameters)

    def request(self,
                href: str,
                method: Optional[str] = 'GET',
                headers: Optional[dict] = {},
                parameters: Optional[dict] = {}) -> str:
        if method == 'POST':
            request = Request(method=method, url=href, headers=headers, json=parameters)
        else:
            params = deepcopy(parameters)
            if 'intersects' in params:
                params['intersects'] = json.dumps(params['intersects'])
            request = Request(method=method, url=href, headers=headers, params=params)
        try:
            prepped = self.session.prepare_request(request)
            msg = f"{prepped.method} {prepped.url} Headers: {prepped.headers}"
            if method == 'POST':
                msg += f" Payload: {json.dumps(request.json)}"
            logger.debug(msg)
            resp = self.session.send(prepped)
            if resp.status_code != 200:
                raise APIError(resp.text)
            return resp.content.decode("utf-8")
        except Exception as err:
            raise APIError(str(err))

    def write_text_to_href(self, href: str, *args: Any, **kwargs: Any) -> None:
        if bool(urlparse(href).scheme):
            raise APIError("Transactions not supported")
        else:
            return super().write_text_to_href(*args, **kwargs)

    def stac_object_from_dict(
        self,
        d: Dict[str, Any],
        href: Optional[str] = None,
        root: Optional["Catalog_Type"] = None,
        preserve_dict: bool = True,
    ) -> "STACObject_Type":
        """Deserializes a :class:`~pystac.STACObject` sub-class instance from a
        dictionary.

        Args:

            d : The dictionary to deserialize
            href : Optional href to associate with the STAC object
            root : Optional root :class:`~pystac.Catalog` to associate with the
                STAC object.
            preserve_dict: If ``False``, the dict parameter ``d`` may be modified
                during this method call. Otherwise the dict is not mutated.
                Defaults to ``True``, which results results in a deepcopy of the
                parameter. Set to ``False`` when possible to avoid the performance
                hit of a deepcopy.
        """
        if identify_stac_object_type(d) == pystac.STACObjectType.ITEM:
            collection_cache = None
            if root is not None:
                collection_cache = root._resolved_objects.as_collection_cache()

            # Merge common properties in case this is an older STAC object.
            merge_common_properties(d, json_href=href, collection_cache=collection_cache)

        info = identify_stac_object(d)
        d = migrate_to_latest(d, info)

        if info.object_type == pystac.STACObjectType.CATALOG:
            result = pystac_client.Client.from_dict(d,
                                                    href=href,
                                                    root=root,
                                                    migrate=False,
                                                    preserve_dict=preserve_dict)
            result._stac_io = self
            return result

        if info.object_type == pystac.STACObjectType.COLLECTION:
            return pystac_client.CollectionClient.from_dict(d,
                                                            href=href,
                                                            root=root,
                                                            migrate=False,
                                                            preserve_dict=preserve_dict)

        if info.object_type == pystac.STACObjectType.ITEM:
            return pystac.Item.from_dict(d,
                                         href=href,
                                         root=root,
                                         migrate=False,
                                         preserve_dict=preserve_dict)

        raise ValueError(f"Unknown STAC object type {info.object_type}")

    def get_pages(self, url, method='GET', parameters={}) -> Iterator[Dict]:
        """Iterator that yields dictionaries for each page at a STAC paging endpoint, e.g., /collections, /search

        Yields
        -------
        Dict : JSON content from a single page
        """
        page = self.read_json(url, method=method, parameters=parameters)
        yield page

        next_link = next((link for link in page.get('links', []) if link['rel'] == 'next'), None)
        while next_link:
            link = Link.from_dict(next_link)
            page = self.read_json(link, parameters=parameters)
            yield page

            # get the next link and make the next request
            next_link = next((link for link in page.get('links', []) if link['rel'] == 'next'),
                             None)

    def assert_conforms_to(self, conformance_class: ConformanceClasses):
        """Whether the API conforms to the given standard. This method only checks against the ``"conformsTo"``
        property from the API landing page and does not make any additional calls to a ``/conformance`` endpoint
        even if the API provides such an endpoint.

        Parameters
        ----------
        key : str
            The ``ConformanceClasses`` key to check conformance against.

        Returns
        -------
        bool
            Indicates if the API conforms to the given spec or URI.
        """
        if not self.conforms_to(conformance_class):
            raise NotImplementedError(f"{conformance_class} not supported")
        else:
            return True

    def conforms_to(self, conformance_class: ConformanceClasses) -> bool:
        """Whether the API conforms to the given standard. This method only checks against the ``"conformsTo"``
        property from the API landing page and does not make any additional calls to a ``/conformance`` endpoint
        even if the API provides such an endpoint.

        Parameters
        ----------
        key : str
            The ``ConformanceClasses`` key to check conformance against.

        Returns
        -------
        bool
            Indicates if the API conforms to the given spec or URI.
        """

        # Conformance of None means ignore all conformance as opposed to an
        #  empty array which would indicate the API conforms to nothing
        if self._conformance is None:
            return True

        uris = CONFORMANCE_URIS.get(conformance_class.name, None)

        if uris is None:
            raise Exception(f"Invalid conformance class {conformance_class}")

        if not any(uri in uris for uri in self._conformance):
            return False

        return True

    def set_conformance(self, conformance: Optional[List[str]]) -> None:
        """Sets (or clears) the conformances for this StacIO."""
        self._conformance = conformance
