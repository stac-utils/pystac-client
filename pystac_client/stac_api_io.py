import json
import logging
import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

import pystac
from pystac.link import Link
from pystac.serialization import (
    identify_stac_object,
    identify_stac_object_type,
    merge_common_properties,
    migrate_to_latest,
)
from pystac.stac_io import DefaultStacIO
from requests import Request, Session

import pystac_client

from .conformance import CONFORMANCE_URIS, ConformanceClasses
from .exceptions import APIError

if TYPE_CHECKING:
    from pystac.catalog import Catalog as Catalog_Type
    from pystac.stac_object import STACObject as STACObject_Type

logger = logging.getLogger(__name__)


class StacApiIO(DefaultStacIO):
    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        conformance: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Initialize class for API IO

        Args:
            headers : Optional dictionary of headers to include in all requests
            conformance : Optional list of `Conformance Classes
                <https://github.com/radiantearth/stac-api-spec/blob/master/overview.md#conformance-classes>`__.
            parameters: Optional dictionary of query string parameters to
              include in all requests.

        Return:
            StacApiIO : StacApiIO instance
        """
        # TODO - this should super() to parent class
        self.session = Session()
        self.session.headers.update(headers or {})
        self.session.params.update(parameters or {})  # type: ignore

        self._conformance = conformance

    def read_text(self, source: pystac.link.HREF, *args: Any, **kwargs: Any) -> str:
        """Read text from the given URI.

        Overwrites the default method for reading text from a URL or file to allow
        :class:`urllib.request.Request` instances as input. This method also raises
        any :exc:`urllib.error.HTTPError` exceptions rather than catching
        them to allow us to handle different response status codes as needed.
        """
        if isinstance(source, Link):
            link = source.to_dict()
            href = link["href"]
            # get headers and body from Link and add to request from simple STAC
            # resolver
            merge = bool(link.get("merge", False))

            # If the link object includes a "method" property, use that. If not
            # fall back to 'GET'.
            method = link.get("method", "GET")
            # If the link object includes a "headers" property, use that and
            # respect the "merge" property.
            headers = link.get("headers", None)

            # If "POST" use the body object that and respect the "merge" property.
            link_body = link.get("body", {})
            if method == "POST":
                parameters = (
                    {**(kwargs.get("parameters", {})), **link_body}
                    if merge
                    else link_body
                )
            else:
                # parameters are already in the link href
                parameters = {}

            return self.request(
                href, method=method, headers=headers, parameters=parameters
            )
        else:  # str or something that can be str'ed
            href = str(source)
            if bool(urlparse(href).scheme):
                return self.request(href, *args, **kwargs)
            else:
                with open(href) as f:
                    href_contents = f.read()
                return href_contents

    def request(
        self,
        href: str,
        method: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Makes a request to an http endpoint

        Args:
            href (str): The request URL
            method (Optional[str], optional): The http method to use, 'GET' or 'POST'.
              Defaults to None, which will result in 'GET' being used.
            headers (Optional[Dict[str, str]], optional): Additional headers to include
                in request. Defaults to None.
            parameters (Optional[Dict[str, Any]], optional): parameters to send with
                request. Defaults to None.

        Raises:
            APIError: raised if the server returns an error response

        Return:
            str: The decoded response from the endpoint
        """
        if method == "POST":
            request = Request(method=method, url=href, headers=headers, json=parameters)
        else:
            params = deepcopy(parameters) or {}
            if "intersects" in params:
                params["intersects"] = json.dumps(params["intersects"])
            request = Request(method="GET", url=href, headers=headers, params=params)
        try:
            prepped = self.session.prepare_request(request)
            msg = f"{prepped.method} {prepped.url} Headers: {prepped.headers}"
            if method == "POST":
                msg += f" Payload: {json.dumps(request.json)}"
            logger.debug(msg)
            resp = self.session.send(prepped)
        except Exception as err:
            raise APIError(str(err))
        if resp.status_code != 200:
            raise APIError.from_response(resp)
        try:
            return resp.content.decode("utf-8")
        except Exception as err:
            raise APIError(str(err))

    def write_text_to_href(self, href: str, *args: Any, **kwargs: Any) -> None:
        if bool(urlparse(href).scheme):
            raise APIError("Transactions not supported")
        else:
            return super().write_text_to_href(href, *args, **kwargs)

    def stac_object_from_dict(
        self,
        d: Dict[str, Any],
        href: Optional[pystac.link.HREF] = None,
        root: Optional["Catalog_Type"] = None,
        preserve_dict: bool = True,
    ) -> "STACObject_Type":
        """Deserializes a :class:`~pystac.STACObject` sub-class instance from a dictionary.

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
            merge_common_properties(
                d, json_href=str(href), collection_cache=collection_cache
            )

        info = identify_stac_object(d)
        d = migrate_to_latest(d, info)

        if info.object_type == pystac.STACObjectType.CATALOG:
            result = pystac_client.client.Client.from_dict(
                d, href=str(href), root=root, migrate=False, preserve_dict=preserve_dict
            )
            result._stac_io = self
            return result

        if info.object_type == pystac.STACObjectType.COLLECTION:
            return pystac_client.collection_client.CollectionClient.from_dict(
                d, href=str(href), root=root, migrate=False, preserve_dict=preserve_dict
            )

        if info.object_type == pystac.STACObjectType.ITEM:
            return pystac.Item.from_dict(
                d, href=str(href), root=root, migrate=False, preserve_dict=preserve_dict
            )

        raise ValueError(f"Unknown STAC object type {info.object_type}")

    def get_pages(
        self,
        url: str,
        method: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Iterator that yields dictionaries for each page at a STAC paging
        endpoint, e.g., /collections, /search

        Return:
            Dict[str, Any] : JSON content from a single page
        """
        page = self.read_json(url, method=method, parameters=parameters)
        yield page

        next_link = next(
            (link for link in page.get("links", []) if link["rel"] == "next"), None
        )
        while next_link:
            link = Link.from_dict(next_link)
            page = self.read_json(link, parameters=parameters)
            yield page

            # get the next link and make the next request
            next_link = next(
                (link for link in page.get("links", []) if link["rel"] == "next"), None
            )

    def assert_conforms_to(self, conformance_class: ConformanceClasses) -> None:
        """Raises a :exc:`NotImplementedError` if the API does not publish the given
        conformance class. This method only checks against the ``"conformsTo"``
        property from the API landing page and does not make any additional
        calls to a ``/conformance`` endpoint even if the API provides such an endpoint.

        Args:
            conformance_class: The ``ConformanceClasses`` key to check conformance
            against.
        """
        if not self.conforms_to(conformance_class):
            raise NotImplementedError(f"{conformance_class} not supported")

    def conforms_to(self, conformance_class: ConformanceClasses) -> bool:
        """Whether the API conforms to the given standard. This method only checks
        against the ``"conformsTo"`` property from the API landing page and does not
        make any additional calls to a ``/conformance`` endpoint even if the API
        provides such an endpoint.

        Args:
            conformance_class : The ``ConformanceClasses`` key to check conformance
                against.

        Return:
            bool: Indicates if the API conforms to the given spec or URI.
        """

        # Conformance of None means ignore all conformance as opposed to an
        #  empty array which would indicate the API conforms to nothing
        if self._conformance is None:
            return True

        class_regex = CONFORMANCE_URIS.get(conformance_class.name, None)

        if class_regex is None:
            raise Exception(f"Invalid conformance class {conformance_class}")

        pattern = re.compile(class_regex)

        if not any(re.match(pattern, uri) for uri in self._conformance):
            return False

        return True

    def set_conformance(self, conformance: Optional[List[str]]) -> None:
        """Sets (or clears) the conformance classes for this StacIO."""
        self._conformance = conformance
