import json
import logging
from copy import deepcopy
from typing import Callable, Iterator, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import requests
from pystac import STAC_IO

from .exceptions import APIError

logger = logging.getLogger(__name__)


def read_text_method(uri):
    """Overwrites the default method for reading text from a URL or file to allow :class:`urllib.request.Request`
    instances as input. This method also raises any :exc:`urllib.error.HTTPError` exceptions rather than catching
    them to allow us to handle different response status codes as needed."""
    if isinstance(uri, Request):
        logger.debug(f"Requesting {uri.get_full_url()} with headers {uri.headers}")
        with urlopen(uri) as response:
            resp = response.read()
        return resp.decode("utf-8")
    elif bool(urlparse(uri).scheme):
        logger.debug(f"Requesting {uri}")
        resp = requests.get(uri)
        return resp.content.decode("utf-8")
    else:
        return STAC_IO.default_read_text_method(uri)


def make_request(session, request, additional_parameters={}):
    _request = deepcopy(request)
    if _request.method == 'POST':
        _request.json.update(additional_parameters)
        logger.debug(
            f"Requesting {_request.url}, Payload: {json.dumps(_request.json)}, Headers: {session.headers}"
        )
    else:
        _request.params.update(additional_parameters)
        logger.debug(
            f"Requesting {_request.url}, Payload: {json.dumps(_request.params)}, Headers: {session.headers}"
        )
    prepped = session.prepare_request(_request)
    resp = session.send(prepped)
    if resp.status_code != 200:
        raise APIError(resp.text)
    return resp.json()


def simple_stac_resolver(link: dict, original_request: requests.Request) -> requests.Request:
    """Handles implementations of the extended STAC ``link`` object as described in the `STAC API - Item Search: Paging
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#paging>`_ documentation. All properties
    described in that spec are considered optional, with fallback values based on the original request.

    This resolver should handle most STAC API - Item Search and OGC API - Features paging implementations.

    If the ``"next"`` link contains ``"body"``, ``"headers"``, or ``"method"`` attributes then these values will be
    used in the respective parts of the next request. If the ``"next"`` link has a ``"merge"`` attribute that is a
    ``True`` boolean value, then these values will be merged with the corresponding values from the original request.
    Otherwise, the ``"merge"`` attribute defaults to ``False`` and these values will overwrite the corresponding
    values from the original request. If any of these attributes are *not present* then the values from the
    original request will be used.

    Parameters
    ----------
    link : dict or pystac.Link
        The ``"next"`` link that was returned in the previous response
    original_request : requests.Request
        The previous requests, which returned the ``"next"`` link used for the ``link`` argument.

    Returns
    -------
    next_request : requests.Request

    Examples
    --------
    >>> import json
    >>> import requests
    >>> from pystac_client.stac_io import simple_stac_resolver
    >>> original_request = urllib.request.Request(
    ...     method='POST',
    ...     url='https://stac-api/search',
    ...     data=json.dumps({'collections': ['my-collection']}).encode('utf-8'),
    ...     headers={'x-custom-header': 'hi-there'}
    ... )

    A link with only an ``"href"`` property.

    >>> next_link = {
    ...     'href': 'https://stac-api/search?next=sometoken',
    ...     'rel': 'next'
    ... }
    >>> next_request = simple_stac_resolver(next_link, original_request)
    >>> next_request.method
    'POST'
    >>> assert next_request.data == original_request.data
    >>> next_request.url
    'https://stac-api/search?next=sometoken'

    Request properties merged from ``"next"`` link. Note that the ``"collections"`` property is not automatically
    transferred from the ``POST`` body to the query string params, it is explicitly given in the links's ``"href"``.

    >>> next_link = {
    ...     'href': 'https://stac-api/search?next=sometoken&collections=my-collection',
    ...     'merge': True,
    ...     'headers': {'x-other-header': 'well-hello'},
    ...     'method': 'GET',
    ...     'rel': 'next'
    ... }
    >>> next_request = simple_stac_resolver(next_link, original_request)
    >>> next_request.method
    'GET'
    >>> next_request.url
    'https://stac-api/search?next=sometoken&collections=my-collection'
    >>> next_request.headers
    {'x-custom-header': 'hi-there', 'x-other-header': 'well-hello'}
    """
    # If the link object includes a "merge" property, use that (we assume it is provided as a boolean value and not
    #  a string). If not, default to False.
    merge = bool(link.get('merge', False))

    # If the link object includes a "method" property, use that. If not fall back to 'GET'.
    method = link.get('method', 'GET')
    # If the link object includes a "headers" property, use that and respect the "merge" property.
    link_headers = link.get('headers')
    headers = original_request.headers
    if link_headers is not None:
        headers = {**headers, **link_headers} if merge else link_headers

    # If "POST" use the body object that and respect the "merge" property.

    if method == 'POST':
        parameters = original_request.json
        link_body = link.get('body', {})
        parameters = {**parameters, **link_body} if merge else link_body
        request = requests.Request(method=method,
                                   url=original_request.url,
                                   headers=headers,
                                   json=parameters)
    else:
        request = requests.Request(method=method,
                                   url=original_request.url,
                                   headers=headers,
                                   params=parameters)

    return request


def get_pages(
    session: requests.Session,
    request: requests.Request,
    next_resolver: Optional[Callable] = simple_stac_resolver,
) -> Iterator[dict]:
    """

    Parameters
    ----------
    session : requests.Session
        requests library Session object
    request : requests.Request
        The initial request to start paging. Subsequent requests will be determined by the ``next_resolver``.
    next_resolver : Callable
        An callable that will be used to construct the request for the next page of results based on the ``"next"``
        link from the previous page.
    """
    while True:
        # Yield all items
        page = make_request(session, request)
        yield page

        # Get the next link and make the next request
        next_link = next((link for link in page.get('links', []) if link['rel'] == 'next'), None)
        if next_link is None:
            break
        request = next_resolver(next_link, request)
