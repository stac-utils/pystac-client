from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
    cast,
)

import pystac
import pystac.validation
from pystac import CatalogType, Collection

from pystac_client._utils import Modifiable, no_modifier
from pystac_client.collection_client import CollectionClient
from pystac_client.conformance import ConformanceClasses
from pystac_client.errors import ClientTypeError
from pystac_client.exceptions import APIError
from pystac_client.item_search import ItemSearch
from pystac_client.stac_api_io import StacApiIO

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
        modifier: Callable[[Modifiable], None] = no_modifier,
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
        ignore_conformance: bool = False,
        modifier: Callable[[Modifiable], None] = no_modifier,
    ) -> "Client":
        """Opens a STAC Catalog or API
        This function will read the root catalog of a STAC Catalog or API

        Args:
            url : The URL of a STAC Catalog. If not specified, this will use the
                `STAC_URL` environment variable.
            headers : A dictionary of additional headers to use in all requests
                made to any part of this Catalog/API.
            parameters: Optional dictionary of query string parameters to
                include in all requests.
            ignore_conformance : Ignore any advertised Conformance Classes in this
                Catalog/API. This means that
                functions will skip checking conformance, and may throw an unknown
                error if that feature is
                not supported, rather than a :class:`NotImplementedError`.
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

        Return:
            catalog : A :class:`Client` instance for this Catalog/API
        """
        client: Client = cls.from_file(
            url, headers=headers, parameters=parameters, modifier=modifier
        )
        search_link = client.get_search_link()
        # if there is a search link, but no conformsTo advertised, ignore
        # conformance entirely
        # NOTE: this behavior to be deprecated as implementations become conformant
        if client._stac_io and (
            ignore_conformance
            or (
                client
                and "conformsTo" not in client.extra_fields.keys()
                and search_link
                and search_link.href
                and len(search_link.href) > 0
            )
        ):
            client._stac_io.set_conformance(None)

        return client

    @classmethod
    def from_file(  # type: ignore
        cls,
        href: str,
        stac_io: Optional[StacApiIO] = None,
        headers: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        modifier: Callable[[Modifiable], None] = no_modifier,
    ) -> "Client":
        """Open a STAC Catalog/API

        Returns:
            Client: A Client (PySTAC Catalog) of the root Catalog for this Catalog/API
        """
        if stac_io is None:
            stac_io = StacApiIO(headers=headers, parameters=parameters)

        client: Client = super().from_file(href, stac_io)  # type: ignore

        client._stac_io._conformance = client.extra_fields.get(  # type: ignore
            "conformsTo", []
        )
        client.modifier = modifier

        return client

    def _supports_collections(self) -> bool:
        return self._conforms_to(ConformanceClasses.COLLECTIONS) or self._conforms_to(
            ConformanceClasses.FEATURES
        )

    def _conforms_to(self, conformance_class: ConformanceClasses) -> bool:
        return self._stac_io.conforms_to(conformance_class)  # type: ignore

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, Any],
        href: Optional[str] = None,
        root: Optional[pystac.Catalog] = None,
        migrate: bool = False,
        preserve_dict: bool = True,
        modifier: Callable[[Modifiable], None] = no_modifier,
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
        # cast require for mypy to believe that we have a Client, rather than
        # the super type.
        # https://github.com/stac-utils/pystac/issues/862
        result = cast(Client, result)

        result.modifier = modifier
        return result

    @lru_cache()
    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """Get a single collection from this Catalog/API

        Args:
            collection_id: The Collection ID to get

        Returns:
            CollectionClient: A STAC Collection
        """
        if self._supports_collections() and self._stac_io:
            url = f"{self.get_self_href()}/collections/{collection_id}"
            collection = CollectionClient.from_dict(
                self._stac_io.read_json(url),
                root=self,
                modifier=self.modifier,
            )
            self.modifier(collection)
            return collection
        else:
            for col in self.get_collections():
                if col.id == collection_id:
                    self.modifier(col)
                    return col

        return None

    def get_collections(self) -> Iterator[Collection]:
        """Get Collections in this Catalog

            Gets the collections from the /collections endpoint if supported,
            otherwise fall back to Catalog behavior of following child links

        Return:
            Iterator[Collection]: Iterator over Collections in Catalog/API
        """
        collection: Union[Collection, CollectionClient]

        if self._supports_collections() and self.get_self_href() is not None:
            url = f"{self.get_self_href()}/collections"
            for page in self._stac_io.get_pages(url):  # type: ignore
                if "collections" not in page:
                    raise APIError("Invalid response from /collections")
                for col in page["collections"]:
                    collection = CollectionClient.from_dict(
                        col, root=self, modifier=self.modifier
                    )
                    self.modifier(collection)
                    yield collection
        else:
            for collection in super().get_collections():
                self.modifier(collection)
                yield collection

    def get_items(self) -> Iterator["Item_Type"]:
        """Return all items of this catalog.

        Return:
            Iterator[Item]:: Iterator of items whose parent is this
                catalog.
        """
        if self._conforms_to(ConformanceClasses.ITEM_SEARCH):
            search = self.search()
            yield from search.items()
        else:
            for item in super().get_items():
                self.modifier(item)
                yield item

    def get_all_items(self) -> Iterator["Item_Type"]:
        """Get all items from this catalog and all subcatalogs. Will traverse
        any subcatalogs recursively, or use the /search endpoint if supported

        Returns:
            Iterator[Item]:: All items that belong to this catalog, and all
                catalogs or collections connected to this catalog through
                child links.
        """
        if self._conforms_to(ConformanceClasses.ITEM_SEARCH):
            # these are already modified
            yield from self.get_items()
        else:
            for item in super().get_items():
                self.modifier(item)
                yield item

    def search(self, **kwargs: Any) -> ItemSearch:
        """Query the ``/search`` endpoint using the given parameters.

        This method returns an :class:`~pystac_client.ItemSearch` instance, see that
        class's documentation for details on how to get the number of matches and
        iterate over results. All keyword arguments are passed directly to the
        :class:`~pystac_client.ItemSearch` instance.

        .. warning::

            This method is only implemented if the API conforms to the
            `STAC API - Item Search
            <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__
            spec *and* contains a link with a ``"rel"`` type of ``"search"`` in its
            root catalog. If the API does not meet either of these criteria, this
            method will raise a :exc:`NotImplementedError`.

        Args:
            **kwargs : Any parameter to the :class:`~pystac_client.ItemSearch` class,
             other than `url`, `conformance`, and `stac_io` which are set from this
             Client instance

        Returns:
            search : An ItemSearch instance that can be used to iterate through Items.

        Raises:
            NotImplementedError: If the API does not conform to the `Item Search spec
                <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__
                or does not have a link with
                a ``"rel"`` type of ``"search"``.
        """
        if not self._conforms_to(ConformanceClasses.ITEM_SEARCH):
            raise NotImplementedError(
                "This catalog does not support search because it "
                f'does not conform to "{ConformanceClasses.ITEM_SEARCH}"'
            )
        search_link = self.get_search_link()
        if search_link:
            if isinstance(search_link.target, str):
                search_href = search_link.target
            else:
                raise NotImplementedError(
                    "Link with rel=search was an object rather than a URI"
                )
        else:
            raise NotImplementedError(
                "No link with rel=search could be found in this catalog"
            )

        return ItemSearch(
            url=search_href,
            stac_io=self._stac_io,
            client=self,
            modifier=self.modifier,
            **kwargs,
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
