import warnings
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
)

from pystac import Collection, Extent

from pystac_client._utils import Modifiable, call_modifier
from pystac_client.conformance import ConformanceClasses
from pystac_client.free_text import sqlite_text_search
from pystac_client.item_search import (
    BaseSearch,
    BBox,
    BBoxLike,
    Datetime,
    DatetimeLike,
    FieldsLike,
    FilterLangLike,
    FilterLike,
    QueryLike,
    SortbyLike,
)
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import DoesNotConformTo, PystacClientWarning

if TYPE_CHECKING:
    from pystac_client import client as _client


TemporalInterval = tuple[Optional[datetime], Optional[datetime]]


def temporal_intervals_overlap(
    interval1: TemporalInterval,
    interval2: TemporalInterval,
) -> bool:
    start1, end1 = interval1
    start2, end2 = interval2
    dtmin = datetime.min.replace(tzinfo=timezone.utc)
    dtmax = datetime.max.replace(tzinfo=timezone.utc)

    return (start2 or dtmin) <= (end1 or dtmax) and (start1 or dtmin) <= (end2 or dtmax)


def bboxes_overlap(bbox1: BBox, bbox2: BBox) -> bool:
    xmin1, ymin1, xmax1, ymax1 = bbox1
    xmin2, ymin2, xmax2, ymax2 = bbox2

    return xmin1 <= xmax2 and xmin2 <= xmax1 and ymin1 <= ymax2 and ymin2 <= ymax1


def _extent_matches(
    extent: Extent,
    bbox: BBox | None = None,
    temporal_interval_str: Datetime | None = None,
) -> tuple[bool, bool]:
    bbox_overlaps = not bbox or (
        any(
            bboxes_overlap(bbox, tuple(collection_bbox))
            for collection_bbox in extent.spatial.bboxes
        )
    )

    # check for overlap between the provided temporal interval and the collection's
    # temporal extent
    collection_temporal_extent = extent.temporal

    # process the user-provided temporal interval
    search_temporal_interval = (
        temporal_interval_str.split("/") if temporal_interval_str else []
    )

    # replace .. in open intervals with actual strings
    if search_temporal_interval:
        if search_temporal_interval[0] == "..":
            search_temporal_interval[0] = datetime.min.replace(
                tzinfo=timezone.utc
            ).isoformat()
        if search_temporal_interval[1] == "..":
            search_temporal_interval[1] = datetime.max.replace(
                tzinfo=timezone.utc
            ).isoformat()

    datetime_overlaps = not temporal_interval_str or (
        any(
            temporal_intervals_overlap(
                (
                    datetime.fromisoformat(
                        search_temporal_interval[0].replace("Z", "+00:00")
                    ),
                    datetime.fromisoformat(
                        search_temporal_interval[1].replace("Z", "+00:00")
                    ),
                ),
                (
                    collection_temporal_interval[0],
                    collection_temporal_interval[1],
                ),
            )
            for collection_temporal_interval in collection_temporal_extent.intervals
        )
    )
    return bbox_overlaps, datetime_overlaps


def collection_matches(
    collection_dict: dict[str, Any],
    bbox: BBox | None = None,
    temporal_interval_str: Datetime | None = None,
    q: str | None = None,
) -> bool:
    # check for overlap between provided bbox and the collection's spatial extent
    try:
        extent = Extent.from_dict(collection_dict.get("extent", {}))
    except Exception:
        warnings.warn(
            f"Unable to parse extent from collection={collection_dict.get('id', None)}",
            PystacClientWarning,
        )
        bbox_overlaps = True
        datetime_overlaps = True
    else:
        bbox_overlaps, datetime_overlaps = _extent_matches(
            extent, bbox, temporal_interval_str
        )

    # check for overlap between the provided free-text search query (q) and the
    # collection's title, description, and keywords
    text_fields: dict[str, str] = {
        key: text
        for key, text in collection_dict.items()
        if text and key in ["title", "description", "keywords"]
    }

    if text_fields.get("keywords"):
        text_fields["keywords"] = ", ".join(text_fields["keywords"])

    text_overlaps = not q or sqlite_text_search(q, text_fields)

    return bbox_overlaps and datetime_overlaps and text_overlaps


class CollectionSearch(BaseSearch):
    """Represents a deferred query to a STAC collection search endpoint as described in
    the `STAC API - Collection Search extension
    <https://github.com/stac-api-extensions/collection-search>`__.

    Due to potential conflicts between the collection-search and transactions extensions
    pystac_client will only send GET requests to the /collections endpoint.

    No request is sent to the API until a method is called to iterate
    through the resulting STAC Collections, either :meth:`CollectionSearch.collections`,
    or :meth:`CollectionSearch.collections_as_dicts`.

    All parameters except `url``, ``method``, ``max_collections``, and ``client``
    correspond to query parameters
    described in the `STAC API - Collection Extension: Query Parameters Table
    <https://github.com/stac-api-extensions/collection-search?tab=readme-ov-file#query-parameters-and-fields>`__
    docs. Please refer to those docs for details on how these parameters filter search
    results.

    Args:
        url: The URL to the search page of the STAC API.
        max_collections : The maximum number of collections to return from the
            search, even if there are more matching results. This client to limit
            the total number of Collections returned from the :meth:`collections`,
            :meth:`collection_list`, and :meth:`collections_as_dicts methods`. The
            client will continue to request pages of collections until the number of
            max collections is reached. Setting this to ``None`` will allow
            iteration over a possibly very large number of results.
        stac_io: An instance of StacIO for retrieving results. Normally comes
            from the Client that returns this CollectionSearch client: An instance of a
            root Client used to set the root on resulting Collections.
        client: An instance of Client for retrieving results. This is normally populated
            by the client that returns this CollectionSearch instance.
        limit: A recommendation to the service as to the number of collections to return
            *per page* of results. Defaults to 100.
        bbox: A list, tuple, or iterator representing a bounding box of 2D
            or 3D coordinates. Results will be filtered
            to only those intersecting the bounding box.
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
        q: Free-text search query. See the `STAC API - Free Text Extension
            Spec <https://github.com/stac-api-extensions/freetext-search>`__ for
            syntax.
        query: List or JSON of query parameters as per the STAC API `query` extension
        filter: JSON of query parameters as per the STAC API `filter` extension
        filter_lang: Language variant used in the filter body. If `filter` is a
            dictionary or not provided, defaults
            to 'cql2-json'. If `filter` is a string, defaults to `cql2-text`.
        sortby: A single field or list of fields to sort the response by
        fields: A list of fields to include in the response. Note this may
            result in invalid STAC objects, as they may not have required fields.
            Use `collections_as_dicts` to avoid object unmarshalling errors.
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
    _collection_search_extension_enabled: bool
    _collection_search_free_text_enabled: bool

    def __init__(
        self,
        url: str,
        *,
        max_collections: int | None = None,
        stac_io: StacApiIO | None = None,
        client: Optional["_client.Client"] = None,
        limit: int | None = None,
        bbox: BBoxLike | None = None,
        datetime: DatetimeLike | None = None,
        query: QueryLike | None = None,
        filter: FilterLike | None = None,
        filter_lang: FilterLangLike | None = None,
        sortby: SortbyLike | None = None,
        fields: FieldsLike | None = None,
        q: str | None = None,
        modifier: Callable[[Modifiable], None] | None = None,
        collection_search_extension_enabled: bool = False,
        collection_search_free_text_enabled: bool = False,
    ):
        super().__init__(
            url=url,
            method="GET",
            max_items=max_collections,
            stac_io=stac_io,
            client=client,
            limit=limit,
            bbox=bbox,
            datetime=datetime,
            query=query,
            filter=filter,
            filter_lang=filter_lang,
            sortby=sortby,
            fields=fields,
            q=q,
            modifier=modifier,
        )

        if client and client._stac_io is not None and stac_io is None:
            self._stac_io = client._stac_io
            self._collection_search_extension_enabled = client.conforms_to(
                ConformanceClasses.COLLECTION_SEARCH
            )
            self._collection_search_free_text_enabled = client.conforms_to(
                ConformanceClasses.COLLECTION_SEARCH_FREE_TEXT
            )
            if any([bbox, datetime, q, query, filter, sortby, fields]):
                if not self._collection_search_extension_enabled:
                    warnings.warn(
                        str(DoesNotConformTo("COLLECTION_SEARCH"))
                        + ". Filtering will be performed client-side where only bbox, "
                        "datetime, and q arguments are supported"
                    )
                    self._validate_client_side_args()
                else:
                    if not self._collection_search_free_text_enabled:
                        warnings.warn(
                            str(DoesNotConformTo("COLLECTION_SEARCH#FREE_TEXT"))
                            + ". Free-text search is not enabled for collection search"
                            "Free-text filters will be applied client-side."
                        )

        else:
            self._stac_io = stac_io or StacApiIO()
            self._collection_search_extension_enabled = (
                collection_search_extension_enabled
            )
            self._collection_search_free_text_enabled = (
                collection_search_free_text_enabled
            )
            self._validate_client_side_args()

    def _validate_client_side_args(self) -> None:
        """Client-side filtering only supports the bbox, datetime, and q parameters."""
        args = {key for key, value in self._parameters.items() if value is not None}
        extras = args - {"bbox", "datetime", "q", "limit", "max_items"}

        if extras:
            raise ValueError(
                "Only the limit, max_collections, bbox, datetime, and q arguments are "
                "supported for client-side filtering but these extra arguments were "
                "provided: " + ",".join(extras)
            )

    @lru_cache(1)
    def matched(self) -> int | None:
        """Return number matched for search

        Returns the value from the `numberMatched` or `context.matched` field.
        Not all APIs will support counts in which case a warning will be issued

        Returns:
            int: Total count of matched collections. If counts are not supported `None`
            is returned.
        """
        found = None
        iter = self.pages_as_dicts()
        page = next(iter, None)

        if not page:
            return 0

        # if collection search and free-text are fully supported, try reading a value
        # from the search result context
        if (
            self._collection_search_extension_enabled
            and self._collection_search_free_text_enabled
        ):
            if "context" in page:
                found = page["context"].get("matched", None)
            elif "numberMatched" in page:
                found = page["numberMatched"]

        if not found:
            count = len(page["collections"])

            for page in iter:
                print(f"found {len(page['collections'])} on the next page")
                count += len(page["collections"])

            found = count

        return found

    # ------------------------------------------------------------------------
    # Result sets
    # ------------------------------------------------------------------------
    # By collection
    def collections(self) -> Iterator[Collection]:
        """Iterator that yields :class:`pystac.Collection` instances for each collection
        matching the given search parameters.

        Yields:
            Collection : each Collection matching the search criteria
        """
        for collection in self.collections_as_dicts():
            # already signed in collections_as_dicts
            yield Collection.from_dict(
                collection, root=self.client, preserve_dict=False
            )

    @lru_cache(1)
    def collections_as_dicts(self) -> Iterator[dict[str, Any]]:
        """Iterator that yields :class:`dict` instances for each collection matching
        the given search parameters.

        Yields:
            Collection : each Collection matching the search criteria
        """
        for page in self.pages_as_dicts():
            yield from page.get("collections", [])

    # ------------------------------------------------------------------------
    # By Page
    def pages(self) -> Iterator[list[Collection]]:
        """Iterator that yields lists of Collection objects.  Each list is
        a page of results from the search.

        Yields:
            List[Collection] : a group of Collections matching the search criteria
        """
        if isinstance(self._stac_io, StacApiIO):
            for page in self.pages_as_dicts():
                # already signed in pages_as_dicts
                yield [
                    Collection.from_dict(
                        collection, preserve_dict=False, root=self.client
                    )
                    for collection in page["collections"]
                ]

    def pages_as_dicts(self) -> Iterator[dict[str, Any]]:
        """Iterator that yields :class:`dict` instances for each page
        of results from the search.

        Yields:
            Dict : a group of collections matching the search
            criteria as a feature-collection-like dictionary.
        """
        if isinstance(self._stac_io, StacApiIO):
            num_collections = 0
            for page in self._stac_io.get_pages(
                self.url, self.method, self.get_parameters()
            ):
                call_modifier(self.modifier, page)
                collections = page.get("collections", [])
                page_has_collections = len(collections) > 0

                # apply client-side filter if the collection search extension
                # is not enabled in the API
                if not self._collection_search_extension_enabled:
                    args = {
                        "bbox": self._parameters.get("bbox"),
                        "temporal_interval_str": self._parameters.get("datetime"),
                        "q": self._parameters.get("q"),
                    }
                    collections = [
                        collection
                        for collection in filter(
                            lambda x: collection_matches(x, **args),
                            collections,
                        )
                    ]

                # apply client-side free-text filter if free-text extension is not
                # enabled in the API
                elif not self._collection_search_free_text_enabled:
                    if q := self._parameters.get("q"):
                        collections = [
                            collection
                            for collection in filter(
                                lambda x: collection_matches(x, q=q),
                                collections,
                            )
                        ]
                if collections:
                    num_collections += len(collections)
                    if self._max_items and num_collections > self._max_items:
                        # Slice the features down to make sure we hit max_collections
                        page["collections"] = collections[
                            0 : -(num_collections - self._max_items)
                        ]
                    else:
                        page["collections"] = collections

                    yield page
                    if self._max_items and num_collections >= self._max_items:
                        return
                # if there were collections on this page but they got filtered out keep
                # going
                elif page_has_collections:
                    continue
                else:
                    return

    # ------------------------------------------------------------------------
    # Everything

    @lru_cache(1)
    def collection_list(self) -> list[Collection]:
        """
        Get the matching collections as a list of :py:class:`pystac.Collection` objects.

        Return:
            List[Collection]: The list of collections
        """
        # Bypass the cache here, so that we can pass __preserve_dict__
        # without mutating what's in the cache.
        collection_list = self.collections_as_dicts.__wrapped__(self)
        # already signed in collections_as_dicts
        return [
            Collection.from_dict(collection, preserve_dict=False, root=self.client)
            for collection in collection_list
        ]

    @lru_cache(1)
    def collection_list_as_dict(self) -> dict[str, Any]:
        """
        Get the matching collections as a dict.

        The dictionary will have a single key:

        1. ``'collections'`` with the value being a list of dictionaries
            for the matching collections.

        Return:
            Dict : A dictionary with the list of matching collections
        """
        collections = []
        for page in self.pages_as_dicts():
            for collection in page["collections"]:
                collections.append(collection)

        return {"collections": collections}
