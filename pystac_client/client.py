import re
import warnings
from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)

import pystac
import pystac.utils
import pystac.validation
from pystac import CatalogType, Collection
from pystac.layout import APILayoutStrategy, HrefLayoutStrategy
from requests import Request

from pystac_client._utils import Modifiable, call_modifier, urljoin
from pystac_client.collection_client import CollectionClient
from pystac_client.collection_search import CollectionSearch
from pystac_client.conformance import ConformanceClasses
from pystac_client.errors import ClientTypeError
from pystac_client.exceptions import APIError
from pystac_client.item_search import (
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
from pystac_client.mixins import QUERYABLES_ENDPOINT, QueryablesMixin
from pystac_client.stac_api_io import StacApiIO, Timeout
from pystac_client.warnings import DoesNotConformTo, FallbackToPystac, NoConformsTo

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

    _stac_io: StacApiIO | None
    _fallback_strategy: HrefLayoutStrategy = APILayoutStrategy()

    def __init__(
        self,
        id: str,
        description: str,
        title: str | None = None,
        stac_extensions: list[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
        href: str | None = None,
        catalog_type: CatalogType = CatalogType.ABSOLUTE_PUBLISHED,
        strategy: HrefLayoutStrategy | None = None,
        *,
        modifier: Callable[[Modifiable], None] | None = None,
        **kwargs: dict[str, Any],
    ):
        super().__init__(
            id,
            description,
            title=title,
            stac_extensions=stac_extensions,
            extra_fields=extra_fields,
            href=href,
            catalog_type=catalog_type,
            strategy=strategy,
            **kwargs,
        )
        self.modifier = modifier

    def __repr__(self) -> str:
        return f"<Client id={self.id}>"

    @classmethod
    def open(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        parameters: dict[str, Any] | None = None,
        ignore_conformance: bool | None = None,
        modifier: Callable[[Modifiable], None] | None = None,
        request_modifier: Callable[[Request], Request | None] | None = None,
        stac_io: StacApiIO | None = None,
        timeout: Timeout | None = None,
    ) -> "Client":
        """Opens a STAC Catalog or API
        This function will read the root catalog of a STAC Catalog or API

        Args:
            url : The URL of a STAC Catalog.
            headers : A dictionary of additional headers to use in all requests
                made to any part of this Catalog/API.
            parameters: Optional dictionary of query string parameters to
                include in all requests.
            ignore_conformance (DEPRECATED) : Ignore any advertised Conformance Classes
                in this Catalog/API. This means that
                functions will skip checking conformance, and may throw an unknown
                error if that feature is
                not supported, rather than a :class:`NotImplementedError`.

                .. deprecated:: 0.7.0
                    Conformance can be altered rather than ignored using methods like
                    :meth:`clear_conforms_to` and :meth:`add_conforms_to`

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
            timeout: Optional float or (float, float) tuple following the semantics
              defined by `Requests
              <https://requests.readthedocs.io/en/latest/api/#main-interface>`__.

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
            timeout=timeout,
        )

        if ignore_conformance is not None:
            warnings.warn(
                (
                    "The `ignore_conformance` option is deprecated and will be "
                    "removed in the next major release. Instead use `set_conforms_to` "
                    "or `add_conforms_to` to control behavior."
                ),
                FutureWarning,
            )

        if not client.has_conforms_to():
            warnings.warn(NoConformsTo())

        return client

    @classmethod
    def from_file(  # type: ignore
        cls,
        href: str,
        stac_io: StacApiIO | None = None,
        headers: dict[str, str] | None = None,
        parameters: dict[str, Any] | None = None,
        modifier: Callable[[Modifiable], None] | None = None,
        request_modifier: Callable[[Request], Request | None] | None = None,
        timeout: Timeout | None = None,
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
                timeout=timeout,
            )
        else:
            stac_io.update(
                headers=headers,
                parameters=parameters,
                request_modifier=request_modifier,
                timeout=timeout,
            )

        client: Client = super().from_file(href, stac_io)
        client.modifier = modifier

        return client

    def has_conforms_to(self) -> bool:
        """Whether server contains list of ``"conformsTo"`` URIs"""
        return "conformsTo" in self.extra_fields

    def get_conforms_to(self) -> list[str]:
        """List of ``"conformsTo"`` URIs

        Return:
            List[str]: List of  URIs that the server conforms to
        """
        return cast(list[str], self.extra_fields.get("conformsTo", []).copy())

    def set_conforms_to(self, conformance_uris: list[str]) -> None:
        """Set list of ``"conformsTo"`` URIs

        Args:
            conformance_uris : URIs indicating what the server conforms to
        """
        self.extra_fields["conformsTo"] = conformance_uris

    def clear_conforms_to(self) -> None:
        """Clear list of ``"conformsTo"`` urls

        Removes the entire list, so :py:meth:`has_conforms_to` will
        return False after using this method.
        """
        self.extra_fields.pop("conformsTo", None)

    def add_conforms_to(self, name: str) -> None:
        """Add ``"conformsTo"`` by name.

        Args:
            name : name of :py:class:`ConformanceClasses` keys to add.
        """
        conformance_class = ConformanceClasses.get_by_name(name)

        if not self.conforms_to(conformance_class):
            self.set_conforms_to([*self.get_conforms_to(), conformance_class.valid_uri])

    def remove_conforms_to(self, name: str) -> None:
        """Remove ``"conformsTo"`` by name.

        Args:
            name : name of :py:class:`ConformanceClasses` keys to remove.
        """
        conformance_class = ConformanceClasses.get_by_name(name)

        self.set_conforms_to(
            [
                uri
                for uri in self.get_conforms_to()
                if not re.match(conformance_class.pattern, uri)
            ]
        )

    def conforms_to(self, conformance_class: ConformanceClasses | str) -> bool:
        """Checks whether the API conforms to the given standard.

        This method only checks
        against the ``"conformsTo"`` property from the API landing page and does not
        make any additional calls to a ``/conformance`` endpoint even if the API
        provides such an endpoint.

        Args:
            name : name of :py:class:`ConformanceClasses` keys to check
                conformance against.

        Return:
            bool: Indicates if the API conforms to the given spec or URI.
        """
        if isinstance(conformance_class, str):
            conformance_class = ConformanceClasses.get_by_name(conformance_class)

        return any(
            re.match(conformance_class.pattern, uri) for uri in self.get_conforms_to()
        )

    @classmethod
    def from_dict(
        cls,
        d: dict[str, Any],
        href: str | None = None,
        root: pystac.Catalog | None = None,
        migrate: bool = False,
        preserve_dict: bool = True,
        modifier: Callable[[Modifiable], None] | None = None,
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

    def _supports_collections(self) -> bool:
        return self.conforms_to(ConformanceClasses.COLLECTIONS) or self.conforms_to(
            ConformanceClasses.FEATURES
        )

    def _warn_about_fallback(self, *args: str) -> None:
        if self.has_conforms_to():
            warnings.warn(DoesNotConformTo(*args), stacklevel=2)
        warnings.warn(FallbackToPystac(), stacklevel=2)

    def get_merged_queryables(self, collections: list[str]) -> dict[str, Any]:
        """Return the set of queryables in common to the specified collections.

        Queryables from multiple collections are unioned together, except in the case
        when the same queryable key has a different definition, in which case that key
        is dropped.

        Output is a dictionary that can be used in ``jsonshema.validate``

        Args:
            collections List[str]: The IDs of the collections to inspect.

        Return:
            Dict[str, Any]: Dictionary containing queryable fields
        """
        if not collections:
            raise ValueError("cannot get_merged_queryables from empty Iterable")

        if not self.conforms_to(ConformanceClasses.FILTER):
            raise DoesNotConformTo(ConformanceClasses.FILTER.name)
        response = self.get_queryables_from(
            self._get_collection_queryables_href(collections[0])
        )
        response.pop("$id")
        addl_props = response.get("additionalProperties", False)
        for collection in collections[1:]:
            resp = self.get_queryables_from(
                self._get_collection_queryables_href(collection)
            )

            # additionalProperties is false if any collection doesn't support additional
            # properties
            addl_props &= resp.get("additionalProperties", False)

            # drop queryables if their keys match, but the descriptions differ
            for k in set(resp["properties"]).intersection(response["properties"]):
                if resp["properties"][k] != response["properties"][k]:
                    resp["properties"].pop(k)
                    response["properties"].pop(k)
            response["properties"].update(resp["properties"])
        return response

    @lru_cache
    def get_collection(self, collection_id: str) -> Collection | CollectionClient:
        """Get a single collection from this Catalog/API

        Args:
            collection_id: The Collection ID to get

        Returns:
            Union[Collection, CollectionClient]: A STAC Collection

        Raises:
            NotFoundError if collection_id does not exist.
        """
        collection: Collection | CollectionClient | None = None

        if self._supports_collections():
            assert self._stac_io is not None

            url = self._collections_href(collection_id)
            collection = CollectionClient.from_dict(
                self._stac_io.read_json(url),
                root=self,
                modifier=self.modifier,
            )
            call_modifier(self.modifier, collection)
        else:
            self._warn_about_fallback("COLLECTIONS", "FEATURES")
            for collection in super().get_collections():
                if collection.id == collection_id:
                    call_modifier(self.modifier, collection)
                    break

        if collection is None:
            raise KeyError(f"Collection {collection_id} not found on catalog")

        return collection

    def get_collections(self) -> Iterator[Collection]:
        """Get Collections in this Catalog

            Gets the collections from the /collections endpoint if supported,
            otherwise fall back to Catalog behavior of following child links

        Return:
            Iterator[Union[Collection, CollectionClient]]: Collections in Catalog/API
        """
        collection: Collection | CollectionClient

        if self._supports_collections():
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
            self._warn_about_fallback("COLLECTIONS", "FEATURES")
            for collection in super().get_collections():
                call_modifier(self.modifier, collection)
                yield collection

    def get_items(
        self, *ids: str, recursive: bool | None = None
    ) -> Iterator["Item_Type"]:
        """Return all items of this catalog.

        Args:
            ids: Zero or more item ids to find.
            recursive: unused in pystac-client, but needed for falling back to pystac

        Return:
            Iterator[Item]: Iterator of items whose parent is this
                catalog.
        """
        if self.conforms_to(ConformanceClasses.ITEM_SEARCH):
            search = self.search(ids=ids)
            yield from search.items()
        else:
            self._warn_about_fallback("ITEM_SEARCH")
            for item in super().get_items(
                *ids, recursive=recursive is None or recursive
            ):
                call_modifier(self.modifier, item)
                yield item

    def get_all_items(self) -> Iterator["Item_Type"]:
        """Get all items from this catalog and all subcatalogs. Will traverse
        any subcatalogs recursively, or use the /search endpoint if supported

        Returns:
            Iterator[Item]: All items that belong to this catalog, and all
                catalogs or collections connected to this catalog through
                child links.
        """
        yield from self.get_items()

    def search(
        self,
        *,
        method: str | None = "POST",
        max_items: int | None = None,
        limit: int | None = None,
        ids: IDsLike | None = None,
        collections: CollectionsLike | None = None,
        bbox: BBoxLike | None = None,
        intersects: IntersectsLike | None = None,
        datetime: DatetimeLike | None = None,
        query: QueryLike | None = None,
        filter: FilterLike | None = None,
        filter_lang: FilterLangLike | None = None,
        sortby: SortbyLike | None = None,
        fields: FieldsLike | None = None,
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
                reached. Setting this to ``None`` will allow iteration over a possibly
                very large number of results.
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
                "ITEM_SEARCH", "There is no fallback option available for search."
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

    def collection_search(
        self,
        *,
        max_collections: int | None = None,
        limit: int | None = None,
        bbox: BBoxLike | None = None,
        datetime: DatetimeLike | None = None,
        q: str | None = None,
        query: QueryLike | None = None,
        filter: FilterLike | None = None,
        filter_lang: FilterLangLike | None = None,
        sortby: SortbyLike | None = None,
        fields: FieldsLike | None = None,
    ) -> CollectionSearch:
        """Query the ``/collections`` endpoint using the given parameters.

        This method returns an :class:`~pystac_client.CollectionSearch` instance. See
        that class's documentation for details on how to get the number of matches and
        iterate over results. The ``url``, `stac_io``, and ``client`` keywords are
        supplied by this Client instance.

        .. warning::

            This method is fully implemented if the API conforms to the
            `STAC API - Collection Search Extension
            <https://github.com/stac-api-extensions/collection-search>`__
            spec.

            If the API does not conform to the Collection Search Extension but
            conforms to `STAC API - Collections <https://api.stacspec.org/v1.0.0/collections/>`__
            (has a ``"rel"`` type of ``"data"`` in its root catalog), a limited
            client-side collection filtering process will be used. If the API does not
            meet either of these criteria, this method will raise a
            :exc:`NotImplementedError`.

            Client-side filtering will only use the ``bbox``, ``datetime``, and ``q``
            (free-text search) parameters.

        Args:
            max_collections : The maximum number of collections to return from the
                search, even if there are more matching results. This client to limit
                the total number of Collections returned from the :meth:`collections`,
                :meth:`collection_list`, and :meth:`collections_as_dicts methods`. The
                client will continue to request pages of collections until the number of
                max collections is reached. Setting this to ``None`` will allow
                iteration over a possibly very large number of results.
            limit: A recommendation to the service as to the number of items to return
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

            q: Free-text search query. See the `STAC API - Free Text Extension
               Spec <https://github.com/stac-api-extensions/freetext-search>`__ for
               details.
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
            collection_search : A CollectionSearch instance that can be used to iterate
            through Collections.

        Raises:
            NotImplementedError: If the API does not conform to either the `STAC API -
                Collection Search spec <https://github.com/stac-api-extensions/collection-search>`__
                or the `STAC API - Collections spec <https://api.stacspec.org/v1.0.0/collections>`__.
        """

        if not (
            self.conforms_to(ConformanceClasses.COLLECTION_SEARCH)
            or self.conforms_to(ConformanceClasses.COLLECTIONS)
        ) and any([bbox, datetime, q, query, filter, sortby, fields]):
            raise DoesNotConformTo(
                "COLLECTION_SEARCH or COLLECTIONS",
                "there is no fallback option available for search.",
            )

        return CollectionSearch(
            url=self._collections_href(),
            client=self,
            max_collections=max_collections,
            limit=limit,
            bbox=bbox,
            datetime=datetime,
            q=q,
            query=query,
            filter=filter,
            filter_lang=filter_lang,
            sortby=sortby,
            fields=fields,
            modifier=self.modifier,
        )

    def get_search_link(self) -> pystac.Link | None:
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
        href = self._get_href("search", search_link, "search")
        return href

    def _collections_href(self, collection_id: str | None = None) -> str:
        data_link = self.get_single_link("data")
        href = self._get_href("data", data_link, "collections")
        if collection_id is not None:
            return urljoin(href, collection_id)
        return href

    def _get_collection_queryables_href(self, collection_id: str | None = None) -> str:
        href = self._collections_href(collection_id)
        return urljoin(href, QUERYABLES_ENDPOINT)
