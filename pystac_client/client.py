from functools import lru_cache
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    cast,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
)
import warnings

import pystac
import pystac.utils
import pystac.validation
from pystac import CatalogType, Collection
from requests import Request

from pystac_client._utils import Modifiable, call_modifier
from pystac_client.collection_client import CollectionClient
from pystac_client.conformance import CONFORMANCE_URIS, ConformanceClasses

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
from pystac_client.mixins import QueryablesMixin
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import (
    DOES_NOT_CONFORM_TO,
    DoesNotConformTo,
    FALLBACK_MSG,
    FallbackToPystac,
    NoConformsTo,
)

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type


class Client(pystac.Catalog, QueryablesMixin):
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

        if not client.has_conforms_to():
            warnings.warn(
                "Server does not advertise any conformance classes.",
                NoConformsTo,
                stacklevel=2,
            )

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
        client.modifier = modifier

        return client

    def has_conforms_to(self) -> bool:
        return bool(self._stac_io and "conformsTo" in self.extra_fields)

    def get_conforms_to(self) -> List[str]:
        return cast(List[str], self.extra_fields.get("conformsTo", []).copy())

    def set_conforms_to(self, conformance_classes: List[str]) -> None:
        self.extra_fields["conformsTo"] = conformance_classes

    def add_conforms_to(
        self, conformance_class: Union[ConformanceClasses, str]
    ) -> None:
        conforms_to = self.get_conforms_to()

        if isinstance(conformance_class, str):
            conformance_class = getattr(
                ConformanceClasses, conformance_class.upper(), conformance_class
            )

        if isinstance(conformance_class, ConformanceClasses):
            conforms_to.append(ConformanceClasses.valid_uri(conformance_class.value))
        else:
            raise Exception(f"Invalid conformance class {conformance_class}")

        self.set_conforms_to(conforms_to)

    def remove_conforms_to(
        self, conformance_class: Union[ConformanceClasses, str]
    ) -> None:
        if isinstance(conformance_class, str):
            name = conformance_class.upper()
        else:
            name = conformance_class.name

        pattern = CONFORMANCE_URIS.get(name, None)

        if pattern is None:
            raise Exception(f"Invalid conformance class {conformance_class}")

        self.set_conforms_to(
            [uri for uri in self.get_conforms_to() if not re.match(pattern, uri)]
        )

    def clear_conforms_to(self) -> None:
        self.extra_fields.pop("conformsTo", None)

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
        pattern = CONFORMANCE_URIS.get(conformance_class.name, None)

        if pattern is None:
            raise Exception(f"Invalid conformance class {conformance_class}")

        if not any(re.match(pattern, uri) for uri in self.get_conforms_to()):
            return False

        return True

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

        if self.conforms_to(ConformanceClasses.COLLECTIONS) or self.conforms_to(
            ConformanceClasses.FEATURES
        ):
            assert self._stac_io is not None

            url = self._collections_href()
            url = f"{url.rstrip('/')}/{collection_id}"
            collection = CollectionClient.from_dict(
                self._stac_io.read_json(url),
                root=self,
                modifier=self.modifier,
            )
            call_modifier(self.modifier, collection)
        else:
            if self.has_conforms_to():
                warnings.warn(
                    DOES_NOT_CONFORM_TO("COLLECTIONS or FEATURES"),
                    category=DoesNotConformTo,
                    stacklevel=2,
                )
            warnings.warn(FALLBACK_MSG, category=FallbackToPystac, stacklevel=2)
            for collection in super().get_collections():
                if collection.id == collection_id:
                    call_modifier(self.modifier, collection)
        return collection

    def get_collections(self) -> Iterator[Collection]:
        """Get Collections in this Catalog

            Gets the collections from the /collections endpoint if supported,
            otherwise fall back to Catalog behavior of following child links

        Return:
            Iterator[Union[Collection, CollectionClient]]: Collections in Catalog/API
        """
        collection: Union[Collection, CollectionClient]

        if self.conforms_to(ConformanceClasses.COLLECTIONS) or self.conforms_to(
            ConformanceClasses.FEATURES
        ):
            assert self._stac_io is not None

            url = self._collections_href()
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
            if self.has_conforms_to():
                warnings.warn(
                    DOES_NOT_CONFORM_TO("COLLECTIONS or FEATURES"),
                    category=DoesNotConformTo,
                    stacklevel=2,
                )
            warnings.warn(FALLBACK_MSG, category=FallbackToPystac, stacklevel=2)
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
            if self.has_conforms_to():
                warnings.warn(
                    DOES_NOT_CONFORM_TO("ITEM_SEARCH"),
                    category=DoesNotConformTo,
                    stacklevel=2,
                )
            warnings.warn(FALLBACK_MSG, category=FallbackToPystac, stacklevel=2)
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

        if not self.conforms_to(ConformanceClasses.ITEM_SEARCH):
            raise DoesNotConformTo(
                f"{DOES_NOT_CONFORM_TO('ITEM_SEARCH')}. "
                "There is not fallback option available for search."
            )

        return ItemSearch(
            url=self._search_href(),
            method=method,
            max_items=max_items,
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

    def _search_href(self) -> str:
        search_link = self.get_search_link()
        href = StacApiIO._get_href(self, "search", search_link, "search")
        return href

    def _collections_href(self) -> str:
        data_link = self.get_single_link("data")
        href = StacApiIO._get_href(self, "data", data_link, "collections")
        return href
