import warnings
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    Optional,
)

from pystac import Item, ItemCollection

from pystac_client._utils import Modifiable, call_modifier
from pystac_client.conformance import ConformanceClasses
from pystac_client.search import (
    BaseSearch,
    BBoxLike,
    CollectionsLike,
    DatetimeLike,
    FieldsLike,
    FilterLangLike,
    FilterLike,
    IDsLike,
    IntersectsLike,
    QueryLike,
    SortbyLike,
)
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import DoesNotConformTo

if TYPE_CHECKING:
    from pystac_client import client as _client


def __getattr__(name: str) -> Any:
    if name in ("DEFAUL_LIMIT", "DEFAULT_LIMIT_AND_MAX_ITEMS"):
        warnings.warn(
            f"{name} is deprecated and will be removed in v0.8", DeprecationWarning
        )
        return 100
    raise AttributeError(f"module {__name__} has no attribute {name}")


class ItemSearch(BaseSearch):
    """Represents a deferred query to a STAC search endpoint as described in the
    `STAC API - Item Search spec
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__.

    No request is sent to the API until a method is called to iterate
    through the resulting STAC Items, either :meth:`ItemSearch.item_collections`,
    :meth:`ItemSearch.items`, or :meth:`ItemSearch.items_as_dicts`.

    All parameters except `url``, ``method``, ``max_items``, and ``client``
    correspond to query parameters
    described in the `STAC API - Item Search: Query Parameters Table
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__
    docs. Please refer
    to those docs for details on how these parameters filter search results.

    Args:
        url: The URL to the search page of the STAC API.
        method : The HTTP method to use when making a request to the service.
            This must be either ``"GET"``, ``"POST"``, or
            ``None``. If ``None``, this will default to ``"POST"``.
            If a ``"POST"`` request receives a ``405`` status for
            the response, it will automatically retry with
            ``"GET"`` for all subsequent requests.
        max_items : The maximum number of items to return from the search, even
            if there are more matching results. This allows the client to limit the
            total number of Items returned from the :meth:`items`,
            :meth:`item_collections`, and :meth:`items_as_dicts methods`. The client
            will continue to request pages of items until the number of max items is
            reached. By default (``max_items=None``) all items matching the query
            will be returned.
        stac_io: An instance of StacIO for retrieving results. Normally comes
            from the Client that returns this ItemSearch client: An instance of a
            root Client used to set the root on resulting Items.
        client: An instance of Client for retrieving results. This is normally populated
            by the client that returns this ItemSearch instance.
        limit: A recommendation to the service as to the number of items to return
            *per page* of results. Defaults to 100.
        ids: List of one or more Item ids to filter on.
        collections: List of one or more Collection IDs or :class:`pystac.Collection`
            instances.
        bbox: A list, tuple, or iterator representing a bounding box of 2D
            or 3D coordinates. Results will be filtered
            to only those intersecting the bounding box.
        intersects: A string or dictionary representing a GeoJSON geometry or feature,
            or an object that implements a ``__geo_interface__`` property, as supported
            by several libraries including Shapely, ArcPy, PySAL, and geojson. Results
            filtered to only those intersecting the geometry.
        datetime: Either a single datetime or datetime range used to filter results.
            You may express a single datetime using a :class:`datetime.datetime`
            instance, a `RFC 3339-compliant <https://tools.ietf.org/html/rfc3339>`__
            timestamp, or a simple date string (see below). Instances of
            :class:`datetime.datetime` may be either
            timezone aware or unaware. Timezone aware instances will be converted to
            a UTC timestamp before being passed
            to the endpoint. Timezone unaware instances are assumed to represent UTC
            timestamps. You may represent a
            datetime range using a ``"/"`` separated string as described in the spec,
            or a list, tuple, or iterator
            of 2 timestamps or datetime instances. For open-ended ranges, use either
            ``".."`` (``'2020-01-01:00:00:00Z/..'``,
            ``['2020-01-01:00:00:00Z', '..']``) or a value of ``None``
            (``['2020-01-01:00:00:00Z', None]``).

            If using a simple date string, the datetime can be specified in
            ``YYYY-mm-dd`` format, optionally truncating
            to ``YYYY-mm`` or just ``YYYY``. Simple date strings will be expanded to
            include the entire time period, for example:

            - ``2017`` expands to ``2017-01-01T00:00:00Z/2017-12-31T23:59:59Z``
            - ``2017-06`` expands to ``2017-06-01T00:00:00Z/2017-06-30T23:59:59Z``
            - ``2017-06-10`` expands to ``2017-06-10T00:00:00Z/2017-06-10T23:59:59Z``

            If used in a range, the end of the range expands to the end of that
            day/month/year, for example:

            - ``2017/2018`` expands to
              ``2017-01-01T00:00:00Z/2018-12-31T23:59:59Z``
            - ``2017-06/2017-07`` expands to
              ``2017-06-01T00:00:00Z/2017-07-31T23:59:59Z``
            - ``2017-06-10/2017-06-11`` expands to
              ``2017-06-10T00:00:00Z/2017-06-11T23:59:59Z``

        query: List or JSON of query parameters as per the STAC API `query` extension
        filter: JSON of query parameters as per the STAC API `filter` extension
        filter_lang: Language variant used in the filter body. If `filter` is a
            dictionary or not provided, defaults
            to 'cql2-json'. If `filter` is a string, defaults to `cql2-text`.
        sortby: A single field or list of fields to sort the response by
        fields: A list of fields to include in the response. Note this may
            result in invalid STAC objects, as they may not have required fields.
            Use `items_as_dicts` to avoid object unmarshalling errors.
        modifier : A callable that modifies the children collection and items
            returned by this Client. This can be useful for injecting
            authentication parameters into child assets to access data
            from non-public sources.

            The callable should expect a single argument, which will be one
            of the following types:

            * :class:`pystac.Collection`
            * :class:`pystac.Item`
            * :class:`pystac.ItemCollection`
            * A STAC item-like :class:`dict`
            * A STAC collection-like :class:`dict`

            The callable should mutate the argument in place and return ``None``.

            ``modifier`` propagates recursively to children of this Client.
            After getting a child collection with, e.g.
            :meth:`Client.get_collection`, the child items of that collection
            will still be signed with ``modifier``.
    """

    _stac_io: StacApiIO

    def __init__(
        self,
        url: str,
        *,
        method: Optional[str] = "POST",
        max_items: Optional[int] = None,
        stac_io: Optional[StacApiIO] = None,
        client: Optional["_client.Client"] = None,
        limit: Optional[int] = None,
        ids: Optional[IDsLike] = None,
        collections: Optional[CollectionsLike] = None,
        bbox: Optional[BBoxLike] = None,
        intersects: Optional[IntersectsLike] = None,
        datetime: Optional[DatetimeLike] = None,
        query: Optional[QueryLike] = None,
        filter: Optional[FilterLike] = None,
        filter_lang: Optional[FilterLangLike] = None,
        sortby: Optional[SortbyLike] = None,
        fields: Optional[FieldsLike] = None,
        modifier: Optional[Callable[[Modifiable], None]] = None,
    ):
        super().__init__(
            url=url,
            method=method,
            max_items=max_items,
            stac_io=stac_io,
            client=client,
            limit=limit,
            ids=ids,
            collections=collections,
            bbox=bbox,
            intersects=intersects,
            datetime=datetime,
            query=query,
            filter=filter,
            filter_lang=filter_lang,
            sortby=sortby,
            fields=fields,
            modifier=modifier,
        )

        if client and client._stac_io is not None and stac_io is None:
            self._stac_io = client._stac_io
            if not client.conforms_to(ConformanceClasses.ITEM_SEARCH):
                warnings.warn(DoesNotConformTo("ITEM_SEARCH"))
        else:
            self._stac_io = stac_io or StacApiIO()

    @lru_cache(1)
    def matched(self) -> Optional[int]:
        """Return number matched for search

        Returns the value from the `numberMatched` or `context.matched` field.
        Not all APIs will support counts in which case a warning will be issued

        Returns:
            int: Total count of matched items. If counts are not supported `None`
            is returned.
        """
        params = {**self.get_parameters(), "limit": 1}
        resp = self._stac_io.read_json(self.url, method=self.method, parameters=params)
        found = None
        if "context" in resp:
            found = resp["context"].get("matched", None)
        elif "numberMatched" in resp:
            found = resp["numberMatched"]
        if found is None:
            warnings.warn("numberMatched or context.matched not in response")
        return found

    # ------------------------------------------------------------------------
    # Result sets
    # ------------------------------------------------------------------------
    # By item
    def items(self) -> Iterator[Item]:
        """Iterator that yields :class:`pystac.Item` instances for each item matching
        the given search parameters.

        Yields:
            Item : each Item matching the search criteria
        """
        for item in self.items_as_dicts():
            # already signed in items_as_dicts
            yield Item.from_dict(item, root=self.client, preserve_dict=False)

    def items_as_dicts(self) -> Iterator[Dict[str, Any]]:
        """Iterator that yields :class:`dict` instances for each item matching
        the given search parameters.

        Yields:
            Item : each Item matching the search criteria
        """
        for page in self.pages_as_dicts():
            for item in page.get("features", []):
                # already signed in pages_as_dicts
                yield item

    # ------------------------------------------------------------------------
    # By Page
    def pages(self) -> Iterator[ItemCollection]:
        """Iterator that yields ItemCollection objects.  Each ItemCollection is
        a page of results from the search.

        Yields:
            ItemCollection : a group of Items matching the search criteria within an
            ItemCollection
        """
        if isinstance(self._stac_io, StacApiIO):
            for page in self.pages_as_dicts():
                # already signed in pages_as_dicts
                yield ItemCollection.from_dict(
                    page, preserve_dict=False, root=self.client
                )

    def pages_as_dicts(self) -> Iterator[Dict[str, Any]]:
        """Iterator that yields :class:`dict` instances for each page
        of results from the search.

        Yields:
            Dict : a group of items matching the search
            criteria as a feature-collection-like dictionary.
        """
        if isinstance(self._stac_io, StacApiIO):
            num_items = 0
            for page in self._stac_io.get_pages(
                self.url, self.method, self.get_parameters()
            ):
                call_modifier(self.modifier, page)
                features = page.get("features", [])
                if features:
                    num_items += len(features)
                    if self._max_items and num_items > self._max_items:
                        # Slice the features down to make sure we hit max_items
                        page["features"] = features[0 : -(num_items - self._max_items)]
                    yield page
                    if self._max_items and num_items >= self._max_items:
                        return
                else:
                    return

    # ------------------------------------------------------------------------
    # Everything

    @lru_cache(1)
    def item_collection(self) -> ItemCollection:
        """
        Get the matching items as a :py:class:`pystac.ItemCollection`.

        Return:
            ItemCollection: The item collection
        """
        # Bypass the cache here, so that we can pass __preserve_dict__
        # without mutating what's in the cache.
        feature_collection = self.item_collection_as_dict.__wrapped__(self)
        # already signed in item_collection_as_dict
        return ItemCollection.from_dict(
            feature_collection, preserve_dict=False, root=self.client
        )

    @lru_cache(1)
    def item_collection_as_dict(self) -> Dict[str, Any]:
        """
        Get the matching items as an item-collection-like dict.

        The dictionary will have two keys:

        1. ``'type'`` with the value ``'FeatureCollection'``
        2. ``'features'`` with the value being a list of dictionaries
            for the matching items.

        Return:
            Dict : A GeoJSON FeatureCollection
        """
        features = []
        for page in self.pages_as_dicts():
            for feature in page["features"]:
                features.append(feature)
        feature_collection = {"type": "FeatureCollection", "features": features}
        return feature_collection

    # Deprecated methods
    # not caching these, since they're cached in the implementation

    def get_item_collections(self) -> Iterator[ItemCollection]:
        """DEPRECATED

        .. deprecated:: 0.4.0
            Use :meth:`ItemSearch.pages` instead.

        Yields:
            ItemCollection : a group of Items matching the search criteria.
        """
        warnings.warn(
            "get_item_collections() is deprecated, use pages() instead",
            FutureWarning,
        )
        return self.pages()

    def item_collections(self) -> Iterator[ItemCollection]:
        """DEPRECATED

        .. deprecated:: 0.5.0
            Use :meth:`ItemSearch.pages` instead.

        Yields:
            ItemCollection : a group of Items matching the search criteria within an
            ItemCollection
        """
        warnings.warn(
            "item_collections() is deprecated, use pages() instead",
            FutureWarning,
        )
        return self.pages()

    def get_items(self) -> Iterator[Item]:
        """DEPRECATED.

        .. deprecated:: 0.4.0
            Use :meth:`ItemSearch.items` instead.

        Yields:
            Item : each Item matching the search criteria
        """
        warnings.warn(
            "get_items() is deprecated, use items() instead",
            FutureWarning,
        )
        return self.items()

    def get_all_items(self) -> ItemCollection:
        """DEPRECATED

        .. deprecated:: 0.4.0
           Use :meth:`ItemSearch.item_collection` instead.

        Return:
            item_collection : ItemCollection
        """
        warnings.warn(
            "get_all_items() is deprecated, use item_collection() instead.",
            FutureWarning,
        )
        return self.item_collection()

    def get_all_items_as_dict(self) -> Dict[str, Any]:
        """DEPRECATED

        .. deprecated:: 0.4.0
           Use :meth:`ItemSearch.item_collection_as_dict` instead.

        Return:
            Dict : A GeoJSON FeatureCollection
        """
        warnings.warn(
            "get_all_items_as_dict() is deprecated, use item_collection_as_dict() "
            "instead.",
            FutureWarning,
        )
        return self.item_collection_as_dict()
