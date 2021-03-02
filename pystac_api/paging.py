"""The functions in this module are designed to work with paginated responses that follow the
`STAC Item Search - Paging spec
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search#paging>`_. The spec leaves many details of
paging up to the service itself, which makes standardizing the handling of response pages difficult on the client
side. This module provides a :func:`simple_stac_resolver` function for working with the most basic implementation of
next links described in the STAC Item Search - Paging spec. This function will also handle ``"next"`` links that simply
provide an ``"href"`` attributes.

For paging implementations not covered by this function, developers can write their own functions (or any callable)
that takes a link and the original request and returns the next request (see the :func:`simple_stac_resolver` for the
required signature and example implementation).
"""
import json
from typing import Callable, Iterator
from urllib.request import Request

from pystac import STAC_IO


def simple_stac_resolver(link: dict, original_request: Request) -> Request:
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
    next_request : urllib.request.Request

    Examples
    --------
    >>> import json
    >>> import urllib.request
    >>> from pystac_api.paging import simple_stac_resolver
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

    # If the link object includes a "method" property, use that. If not, use the method kwarg that was
    #  provided to the __init__ method. If no method kwarg was provided, fall back to 'GET'.
    method = link.get('method', original_request.method)
    if 'body' in link:
        # Infer a POST request if a "body" parameter is present in the "next" link
        method = 'POST'

    # If the link object includes a "headers" property, use that and respect the "merge" property. If not,
    #  use the headers from the original request.
    headers = original_request.headers
    link_headers = link.get('headers')
    if link_headers is not None:
        headers = {**headers, **link_headers} if merge else link_headers

    # If the link object includes a "body" property, use that and respect the "merge" property. If not,
    #  use the JSON body from the original request.
    data = None
    if original_request.data is not None and method == 'POST':
        data = json.loads(original_request.data.decode('utf-8'))
    link_body = link.get('body')
    if link_body is not None:
        if data is None:
            data = link_body
        else:
            data = {**data, **link_body} if merge else link_body
    if data is not None:
        data = json.dumps(data).encode('utf-8')

    return Request(
        method=method,
        url=link['href'],
        data=data,
        headers=headers
    )


def paginate(
    request: Request,
    next_resolver: Callable,
) -> Iterator[dict]:
    """

    Parameters
    ----------
    request : urllib.request.Request
        The initial request to start paging. Subsequent requests will be determined by the ``next_resolver``.
    next_resolver : Callable
        An callable that will be used to construct the request for the next page of results based on the ``"next"``
        link from the previous page.
    """
    while True:
        # Yield all items
        page = STAC_IO.read_json(request)
        yield page

        # Get the next link and make the next request
        next_link = next((link for link in page.get('links', []) if link['rel'] == 'next'), None)
        if next_link is None:
            break
        request = next_resolver(next_link, request)
