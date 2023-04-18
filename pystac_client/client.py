from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Union
import warnings

import pystac
import pystac.utils
import pystac.validation
from pystac import CatalogType, Collection
from requests import Request

from pystac_client._utils import Modifiable, call_modifier
from pystac_client.collection_client import CollectionClient
from pystac_client.conformance import ConformanceClasses
from pystac_client.errors import ClientTypeError
from pystac_client.exceptions import APIError
from pystac_client.item_search import (
    DEFAULT_LIMIT_AND_MAX_ITEMS,
    BBoxLike,
    CollectionsLike,
    DatetimeLike,
    FieldsLike,
    FilterLangLike,
    FilterLike,
    IDsLike,
    IntersectsLike,
    ItemSearch,
    QueryLike,
    SortbyLike,
)
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import (
    FALLBACK_MSG,
    FallbackToPystac,
    MissingLink,
    NoConformsTo,
)

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type


class Client(pystac.Catalog):
    """A Client for interacting with the root of a STAC Catalog or API

    Instances of the ``Client`` class inherit from :class:`pystac.Catalog`
    and provide a convenient way of interacting
    with STAC Catalogs OR STAC APIs that conform to the `STAC API spec
    <https://github.com/radiantearth/stac-api-spec>`_.
    In addition to being a valid
    `STAC Catalog
    <https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/catalog-spec.md>`_
    APIs that have a ``"conformsTo"`` indicate that it supports additional
    functionality on top of a normal STAC Catalog,
    such as searching items (e.g., /search endpoint).
    """

    _stac_io: Optional[StacApiIO]

    def __init__(
        self,
        id: str,
        description: str,
        title: Optional[str] = None,
        stac_extensions: Optional[List[str]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
        href: Optional[str] = None,
        catalog_type: CatalogType = CatalogType.ABSOLUTE_PUBLISHED,
        *,
        modifier: Optional[Callable[[Modifiable], None]] = None,
        **kwargs: Dict[str, Any],
    ):
        super().__init__(
            id,
            description,
            title=title,
            stac_extensions=stac_extensions,
            extra_fields=extra_fields,
            href=href,
            catalog_type=catalog_type,
            **kwargs,
        )
        self.modifier = modifier

    def __repr__(self) -> str:
        return "<Client id={}>".format(self.id)

    @classmethod
    def open(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        modifier: Optional[Callable[[Modifiable], None]] = None,
        request_modifier: Optional[Callable[[Request], Union[Request, None]]] = None,
        stac_io: Optional[StacApiIO] = None,
    ) -> "Client":
        """Opens a STAC Catalog or API
        This function will read the root catalog of a STAC Catalog or API

        Args:
            url : The URL of a STAC Catalog.
            headers : A dictionary of additional headers to use in all requests
                made to any part of this Catalog/API.
            parameters: Optional dictionary of query string parameters to
                include in all requests.
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
            request_modifier: A callable that either modifies a `Request` instance or
                returns a new one. This can be useful for injecting Authentication
                headers and/or signing fully-formed requests (e.g. signing requests
                using AWS SigV4).

                The callable should expect a single argument, which will be an instance
                of :class:`requests.Request`.

                If the callable returns a `requests.Request`, that will be used.
                Alternately, the callable may simply modify the provided request object
                and return `None`.
            stac_io: A `StacApiIO` object to use for I/O requests. Generally, leave
                this to the default. However in cases where customized I/O processing
                is required, a custom instance can be provided here.

        Return:
            catalog : A :class:`Client` instance for this Catalog/API
        """
        client: Client = cls.from_file(
            url,
            headers=headers,
            parameters=parameters,
            modifier=modifier,
            request_modifier=request_modifier,
            stac_io=stac_io,
        )

        if client._stac_io and (
            "conformsTo" not in client.extra_fields.keys() and client._get_search_href()
        ):
            warnings.warn(
                "Server does not advertise any conformance classes.",
                NoConformsTo,
            )
            client._stac_io.set_conformance(None)

        return client

    @classmethod
    def from_file(  # type: ignore
        cls,
        href: str,
        stac_io: Optional[StacApiIO] = None,
        headers: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        modifier: Optional[Callable[[Modifiable], None]] = None,
        request_modifier: Optional[Callable[[Request], Union[Request, None]]] = None,
    ) -> "Client":
        """Open a STAC Catalog/API

        Returns:
            Client: A Client (PySTAC Catalog) of the root Catalog for this Catalog/API
        """
        if stac_io is None:
            stac_io = StacApiIO(
                headers=headers,
                parameters=parameters,
                request_modifier=request_modifier,
            )
        else:
            stac_io.update(
                headers=headers,
                parameters=parameters,
                request_modifier=request_modifier,
            )

        client: Client = super().from_file(href, stac_io)

        client._stac_io._conformance = client.extra_fields.get(  # type: ignore
            "conformsTo", []
        )
        client.modifier = modifier

        return client

    def conforms_to(self, *conformance_classes: ConformanceClasses) -> bool:
        return bool(self._stac_io and self._stac_io.conforms_to(*conformance_classes))

    def _supports_collections(self) -> bool:
        return self.conforms_to(
            ConformanceClasses.COLLECTIONS, ConformanceClasses.FEATURES
        )

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, Any],
        href: Optional[str] = None,
        root: Optional[pystac.Catalog] = None,
        migrate: bool = False,
        preserve_dict: bool = True,
        modifier: Optional[Callable[[Modifiable], None]] = None,
    ) -> "Client":
        try:
            # this will return a Client because we have used a StacApiIO instance
            result = super().from_dict(
                d=d, href=href, root=root, migrate=migrate, preserve_dict=preserve_dict
            )
        except pystac.STACTypeError:
            raise ClientTypeError(
                f"Could not open Client (href={href}), "
                f"expected type=Catalog, found type={d.get('type', None)}"
            )

        result.modifier = modifier
        return result

    @lru_cache()
    def get_collection(
        self, collection_id: str
    ) -> Optional[Union[Collection, CollectionClient]]:
        """Get a single collection from this Catalog/API

        Args:
            collection_id: The Collection ID to get

        Returns:
            Union[Collection, CollectionClient]: A STAC Collection
        """
        collection: Union[Collection, CollectionClient]

        if self._supports_collections() and self._stac_io:
            url = self._get_collections_href(collection_id)
            collection = CollectionClient.from_dict(
                self._stac_io.read_json(url),
                root=self,
                modifier=self.modifier,
            )
            call_modifier(self.modifier, collection)
            return collection
        else:
            warnings.warn(FALLBACK_MSG, category=FallbackToPystac)
            for collection in super().get_collections():
                if collection.id == collection_id:
                    call_modifier(self.modifier, collection)
                    return collection

        return None

    def get_collections(self) -> Iterator[Union[Collection, CollectionClient]]:
        """Get Collections in this Catalog

            Gets the collections from the /collections endpoint if supported,
            otherwise fall back to Catalog behavior of following child links

        Return:
            Iterator[Union[Collection, CollectionClient]]: Collections in Catalog/API
        """
        collection: Union[Collection, CollectionClient]

        if self._supports_collections() and self._stac_io:
            url = self._get_collections_href()
            for page in self._stac_io.get_pages(url):
                if "collections" not in page:
                    raise APIError("Invalid response from /collections")
                for col in page["collections"]:
                    collection = CollectionClient.from_dict(
                        col, root=self, modifier=self.modifier
                    )
                    call_modifier(self.modifier, collection)
                    yield collection
        else:
            warnings.warn(FALLBACK_MSG, category=FallbackToPystac)
            for collection in super().get_collections():
                call_modifier(self.modifier, collection)
                yield collection

    def get_items(self) -> Iterator["Item_Type"]:
        """Return all items of this catalog.

        Return:
            Iterator[Item]:: Iterator of items whose parent is this
                catalog.
        """
        if self.conforms_to(ConformanceClasses.ITEM_SEARCH):
            search = self.search()
            yield from search.items()
        else:
            warnings.warn(FALLBACK_MSG, category=FallbackToPystac)
            for item in super().get_items():
                call_modifier(self.modifier, item)
                yield item

    def get_all_items(self) -> Iterator["Item_Type"]:
        """Get all items from this catalog and all subcatalogs. Will traverse
        any subcatalogs recursively, or use the /search endpoint if supported

        Returns:
            Iterator[Item]:: All items that belong to this catalog, and all
                catalogs or collections connected to this catalog through
                child links.
        """
        yield from self.get_items()

    def search(
        self,
        *,
        method: Optional[str] = "POST",
        max_items: Optional[int] = None,
        limit: Optional[int] = DEFAULT_LIMIT_AND_MAX_ITEMS,
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
    ) -> ItemSearch:
        """Query the ``/search`` endpoint using the given parameters.

        This method returns an :class:`~pystac_client.ItemSearch` instance. See that
        class's documentation for details on how to get the number of matches and
        iterate over results. The ``url``, `stac_io``, and ``client`` keywords are
        supplied by this Client instance.

        .. warning::

            This method is only implemented if the API conforms to the
            `STAC API - Item Search
            <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__
            spec *and* contains a link with a ``"rel"`` type of ``"search"`` in its
            root catalog. If the API does not meet either of these criteria, this
            method will raise a :exc:`NotImplementedError`.

        Args:
            method : The HTTP method to use when making a request to the service.
                This must be either ``"GET"``, ``"POST"``, or
                ``None``. If ``None``, this will default to ``"POST"``.
                If a ``"POST"`` request receives a ``405`` status for
                the response, it will automatically retry with
                ``"GET"`` for all subsequent requests.
            max_items : The maximum number of items to return from the search, even
                if there are more matching results. This client to limit the
                total number of Items returned from the :meth:`items`,
                :meth:`item_collections`, and :meth:`items_as_dicts methods`. The client
                will continue to request pages of items until the number of max items is
                reached. This parameter defaults to 100. Setting this to ``None`` will
                allow iteration over a possibly very large number of results.
            limit: A recommendation to the service as to the number of items to return
                *per page* of results. Defaults to 100.
            ids: List of one or more Item ids to filter on.
            collections: List of one or more Collection IDs or
                :class:`pystac.Collection` instances. Only Items in one
                of the provided Collections will be searched
            bbox: A list, tuple, or iterator representing a bounding box of 2D
                or 3D coordinates. Results will be filtered
                to only those intersecting the bounding box.
            intersects: A string or dictionary representing a GeoJSON geometry, or
                an object that implements a
                ``__geo_interface__`` property, as supported by several libraries
                including Shapely, ArcPy, PySAL, and
                geojson. Results filtered to only those intersecting the geometry.
            datetime: Either a single datetime or datetime range used to filter results.
                You may express a single datetime using a :class:`datetime.datetime`
                instance, a `RFC 3339-compliant <https://tools.ietf.org/html/rfc3339>`__
                timestamp, or a simple date string (see below). Instances of
                :class:`datetime.datetime` may be either
                timezone aware or unaware. Timezone aware instances will be converted to
                a UTC timestamp before being passed
                to the endpoint. Timezone unaware instances are assumed to represent UTC
                timestamps. You may represent a
                datetime range using a ``"/"`` separated string as described in the
                spec, or a list, tuple, or iterator
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
                - ``2017-06-10`` expands to
                  ``2017-06-10T00:00:00Z/2017-06-10T23:59:59Z``

                If used in a range, the end of the range expands to the end of that
                day/month/year, for example:

                - ``2017/2018`` expands to
                  ``2017-01-01T00:00:00Z/2018-12-31T23:59:59Z``
                - ``2017-06/2017-07`` expands to
                  ``2017-06-01T00:00:00Z/2017-07-31T23:59:59Z``
                - ``2017-06-10/2017-06-11`` expands to
                  ``2017-06-10T00:00:00Z/2017-06-11T23:59:59Z``

            query: List or JSON of query parameters as per the STAC API `query`
                extension
            filter: JSON of query parameters as per the STAC API `filter` extension
            filter_lang: Language variant used in the filter body. If `filter` is a
                dictionary or not provided, defaults
                to 'cql2-json'. If `filter` is a string, defaults to `cql2-text`.
            sortby: A single field or list of fields to sort the response by
            fields: A list of fields to include in the response. Note this may
                result in invalid STAC objects, as they may not have required fields.
                Use `items_as_dicts` to avoid object unmarshalling errors.

        Returns:
            search : An ItemSearch instance that can be used to iterate through Items.

        Raises:
            NotImplementedError: If the API does not conform to the `Item Search spec
                <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__
                or does not have a link with
                a ``"rel"`` type of ``"search"``.
        """
        return ItemSearch(
            url=self._get_search_href(),
            method=method,
            max_items=max_items,
            stac_io=self._stac_io,
            client=self,
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
            modifier=self.modifier,
        )

    def get_search_link(self) -> Optional[pystac.Link]:
        """Returns this client's search link.

        Searches for a link with rel="search" and either a GEOJSON or JSON media type.

        Returns:
            Optional[pystac.Link]: The search link, or None if there is not one found.
        """
        return next(
            (
                link
                for link in self.links
                if link.rel == "search"
                and (
                    link.media_type == pystac.MediaType.GEOJSON
                    or link.media_type == pystac.MediaType.JSON
                )
            ),
            None,
        )

    def _get_search_href(self) -> str:
        search_link = self.get_search_link()
        href = self._get_href("search", search_link, "search")
        return href

    def _get_collections_href(self, collection_id: Optional[str] = None) -> str:
        data_link = self.get_single_link("data")
        href = self._get_href("data", data_link, "collections")
        if collection_id is None:
            return href
        else:
            return f"{href.rstrip('/')}/{collection_id}"

    def _get_href(self, rel: str, link: Optional[pystac.Link], endpoint: str) -> str:
        if link and isinstance(link.href, str):
            href = link.href
            if not pystac.utils.is_absolute_href(href):
                href = pystac.utils.make_absolute_href(href, self.self_href)
        else:
            warnings.warn(
                f"No link with {rel=} could be found in this catalog",
                category=MissingLink,
            )
            href = f"{self.self_href.rstrip('/')}/{endpoint}"
        return href
