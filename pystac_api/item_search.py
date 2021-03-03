import itertools as it
import json
from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime as datetime_
from typing import Callable, Iterator, List, Optional, Tuple, Union
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from urllib.request import Request

import pystac
import pytz

from pystac_api.paging import paginate, simple_stac_resolver

DatetimeOrTimestamp = Optional[Union[datetime_, str]]
Datetime = Union[Tuple[str], Tuple[str, str]]
DatetimeLike = Union[
    DatetimeOrTimestamp,
    Tuple[DatetimeOrTimestamp, DatetimeOrTimestamp],
    List[DatetimeOrTimestamp],
    Iterator[DatetimeOrTimestamp]
]

BBox = Tuple[float, ...]
BBoxLike = Union[BBox, List[float], Iterator[float], str]

Collections = Tuple[str, ...]
CollectionsLike = Union[
    List[Union[str, pystac.Collection]],
    Iterator[Union[str, pystac.Collection]],
    str,
    pystac.Collection
]

IDs = Tuple[str, ...]
IDsLike = Union[IDs, str, List[str], Iterator[str]]

Intersects = dict
IntersectsLike = Union[str, Intersects, object]


class ItemSearch:
    """Represents a query to an Item Search endpoint as described in the `STAC API - Item Search spec
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__.

    Instances of this class are iterators that will yield :class:`pystac.Item` instances for each item matched
    by the search parameters. The instance handles paging through responses from the API until either all matched items
    have been yielded or the specified maximum number of items has been reached.

    If ``intersects`` is included in the search parameters, then the instance will first try to make a ``POST`` request.
    If server responds with a ``405 - Method Not Allowed`` status code, then the instance will fall back to using
    ``GET`` requests for all subsequent requests.

    All parameters, with the exception of ``max_items`` map to the corresponding query parameters describes in the
    `STAC API - Item Search: Query Parameters Table
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__ docs. Please refer
    to those docs for details on how these parameters filter search results.

    Parameters
    ----------
    url : str
        The URL to the item-search endpoint
    limit : int, optional
        The maximum number of items to return *per page*. Defaults to ``None``, which falls back to the limit set by the
        service.
    bbox: list or tuple or Iterator or str, optional
        May be a list, tuple, or iterator representing a bounding box of 2D or 3D coordinates. Results will be filtered
        to only those intersecting the bounding box.
    datetime: str or datetime.datetime or list or tuple or Iterator, optional
        Either a single datetime or datetime range used to filter results. You may express a single datetime using
        a :class:`datetime.datetime` instance or a `RFC 3339-compliant <https://tools.ietf.org/html/rfc3339>`__
        timestamp. Instances of :class:`datetime.datetime` may be either timezone aware or unaware. Timezone aware
        instances will be converted to a UTC timestamp before being passed to the endpoint. Timezone unaware instances
        are assumed to represent UTC timestamps.
        You may represent a datetime range using a ``"/"`` separated string as described in the spec, or a list, tuple,
        or iterator of 2 timestamps or datetime instances. For open-ended ranges, use either ``".."``
        (``'2020-01-01:00:00:00Z/..'``, ``['2020-01-01:00:00:00Z', '..']``) or a value of ``None``
        (``['2020-01-01:00:00:00Z', None]``).
    intersects: str or dict, optional
        A GeoJSON-like dictionary or JSON string. Results will be filtered to only those intersecting the geometry
    ids: list, optional
        List of Item ids to return. All other filter parameters that further restrict the number of search results
        (except ``limit``) are ignored.
    collections: list, optional
        List of one or more Collection IDs or :class:`pystac.Collection` instances. Only Items in one of the provided
        Collections will be searched
    max_items : int or None, optional
        The maximum number of items to return from the search. *Note that this is not a STAC API - Item Search parameter
        and is instead used by the client to limit the total number of returned items*.
    method : str or None, optional
        The HTTP method to use when making a request to the service. This must be either ``"GET"``, ``"POST"``, or
        ``None``. If ``None``, this will default to ``"POST"`` if the ``intersects`` argument is present and ``"GET"``
        if not. If a ``"POST"`` request receives a ``405`` status for the response, it will automatically retry with a
        ``"GET"`` request for all subsequent requests.
    next_resolver: Callable, optional
        A callable that will be used to construct the next request based on a "next" link and the previous request.
        Defaults to using the :func:`~pystac_api.paging.simple_stac_resolver`.

    Yields
    ------
    item : pystac.Item
    """
    def __init__(
        self,
        url: str,
        *,
        limit: Optional[int] = None,
        bbox: Optional[BBoxLike] = None,
        datetime: Optional[DatetimeLike] = None,
        intersects: Optional[IntersectsLike] = None,
        ids: Optional[IDsLike] = None,
        collections: Optional[CollectionsLike] = None,
        max_items: Optional[int] = None,
        method: Optional[str] = None,
        next_resolver: Callable = simple_stac_resolver
    ):
        # If method is not provided, determine based on presence of "intersects" argument
        if method is None:
            method = 'POST' if intersects is not None else 'GET'
        self._method = method
        self._next_resolver = next_resolver
        self._url = url
        self._max_items = max_items

        self._search_parameters = {
            'limit': int(limit) if limit is not None else None,
            'bbox': self._format_bbox(bbox),
            'datetime': self._format_datetime(datetime),
            'ids': self._format_ids(ids),
            'collections': self._format_collections(collections),
            'intersects': self._format_intersects(intersects)
        }

    @property
    def url(self):
        return str(self._url)

    @property
    def method(self):
        """The HTTP method/verb that will be used when making requests."""
        return str(self._method)

    @staticmethod
    def _format_bbox(value: Optional[BBoxLike]) -> Optional[BBox]:
        if value is None:
            return None

        if isinstance(value, str):
            bbox = tuple(map(float, value.split(',')))
        else:
            bbox = tuple(map(float, value))

        return bbox

    @staticmethod
    def _format_datetime(value: Optional[DatetimeLike]) -> Optional[Datetime]:
        def _format(dt):
            if dt is None:
                return '..'
            if isinstance(dt, str):
                return dt

            if dt.tzinfo is not None:
                dt = dt.astimezone(pytz.UTC)
                dt = dt.replace(tzinfo=None)

            return dt.isoformat('T') + 'Z'

        if value is None:
            return None
        if isinstance(value, str):
            return tuple(map(_format, value.split('/')))
        if isinstance(value, Iterable):
            return tuple(map(_format, value))

        return _format(value),

    @staticmethod
    def _format_collections(value: Optional[CollectionsLike]) -> Optional[Collections]:
        def _format(c):
            if isinstance(c, str):
                return c
            if isinstance(c, Iterable):
                return tuple(map(_format, c))

            return c.id

        if value is None:
            return None
        if isinstance(value, str):
            return tuple(map(_format, value.split(',')))
        if isinstance(value, pystac.Collection):
            return _format(value),

        return _format(value)

    @staticmethod
    def _format_ids(value: Optional[IDsLike]) -> Optional[IDs]:
        if value is None:
            return None

        if isinstance(value, str):
            return tuple(value.split(','))

        return tuple(value)

    @staticmethod
    def _format_intersects(value: Optional[IntersectsLike]) -> Optional[Intersects]:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return deepcopy(getattr(value, '__geo_interface__', value))

    @property
    def search_parameters(self) -> dict:
        return deepcopy(self._search_parameters)

    @property
    def search_parameters_get(self) -> dict:
        """A dictionary containing all parameters associated with this search, formatted to be passed as query string
        parameters in a ``"GET"`` request according to the requirements in the `Query Parameters and Fields
        <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameters-and-fields>`__ docs."""
        return {
            param: '/'.join(map(str, value)) if param == 'datetime'
                   else ','.join(map(str, value)) if type(value) is tuple
                   else value
            for param, value in self.search_parameters.items()
            if value is not None
        }

    @property
    def search_parameters_post(self) -> dict:
        """A dictionary containing all parameters associated with this search, formatted to be passed in the body of a
        ``POST`` request."""
        return {
            key: value
            for key, value in self.search_parameters.items()
            if value is not None
        }

    def item_collections(self) -> Iterator[dict]:
        """Iterator that yields dictionaries matching the `ItemCollection
        <https://github.com/radiantearth/stac-api-spec/blob/master/fragments/itemcollection/README.md>`__ spec. Each of
        these items represents a "page" or results for the search.

        Yields
        -------
        page : dict
        """
        if self.method == 'GET':
            parsed = urlsplit(self.url)

            # Format search params as query parameters
            params = {
                **parse_qs(parsed.query),
                **self.search_parameters_get
            }
            url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), None))
            request = Request(method='GET', url=url)
        else:
            request = Request(
                method='POST',
                url=self.url,
                data=json.dumps(self.search_parameters_post).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
        for page in paginate(
            request=request,
            next_resolver=self._next_resolver
        ):
            self._current_page = page
            yield page

    def __iter__(self) -> Iterator[pystac.Item]:
        """Iterates over the search results by paging through the responses and yielding items
        from each."""
        def _paginate():
            for page in self.item_collections():
                yield from map(pystac.Item.from_dict, page.get('features'))

        try:
            yield from it.islice(_paginate(), self._max_items)
        except HTTPError as e:
            if e.code == 405:
                self._method = 'GET'
                yield from it.islice(_paginate(), self._max_items)
            else:
                raise
