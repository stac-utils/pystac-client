from typing import Any, Iterable, Dict, Optional, TYPE_CHECKING

import pystac
import pystac.validation
from pystac_client.collection_client import CollectionClient

from pystac_client.conformance import ConformanceClasses
from pystac_client.exceptions import APIError
from pystac_client.item_search import ItemSearch
from pystac_client.stac_api_io import StacApiIO

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type


class Client(pystac.Catalog):
    """A Client for interacting with the root of a STAC Catalog or API

    Instances of the ``Client`` class inherit from :class:`pystac.Catalog` and provide a convenient way of interacting
    with STAC Catalogs OR STAC APIs that conform to the `STAC API spec <https://github.com/radiantearth/stac-api-spec>`_.
    In addition to being a valid
    `STAC Catalog <https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/catalog-spec.md>`_
    APIs that have a ``"conformsTo"`` indicate that it supports additional functionality on top of a normal STAC Catalog,
    such as searching items (e.g., /search endpoint).
    """
    def __repr__(self):
        return '<Client id={}>'.format(self.id)

    @classmethod
    def open(cls,
             url: str,
             headers: Dict[str, str] = None,
             ignore_conformance: bool = False) -> "Client":
        """Opens a STAC Catalog or API
        This function will read the root catalog of a STAC Catalog or API

        Args:
            url : The URL of a STAC Catalog. If not specified, this will use the `STAC_URL` environment variable.
            headers : A dictionary of additional headers to use in all requests made to any part of this Catalog/API.
            ignore_conformance : Ignore any advertised Conformance Classes in this Catalog/API. This means that
                functions will skip checking conformance, and may throw an unknown error if that feature is
                not supported, rather than a :class:`NotImplementedError`.

        Return:
            catalog : A :class:`Client` instance for this Catalog/API
        """
        cat = cls.from_file(url, headers=headers)
        search_link = cat.get_links('search')
        # if there is a search link, but no conformsTo advertised, ignore conformance entirely
        # NOTE: this behavior to be deprecated as implementations become conformant
        if ignore_conformance or ('conformsTo' not in cat.extra_fields.keys()
                                  and len(search_link) > 0):
            cat._stac_io.set_conformance(None)
        return cat

    @classmethod
    def from_file(cls,
                  href: str,
                  stac_io: Optional[pystac.StacIO] = None,
                  headers: Optional[Dict] = {}) -> "Client":
        """Open a STAC Catalog/API

        Returns:
            Client: A Client (PySTAC Catalog) of the root Catalog for this Catalog/API
        """
        if stac_io is None:
            stac_io = StacApiIO(headers=headers)

        cat = super().from_file(href, stac_io)

        cat._stac_io._conformance = cat.extra_fields.get('conformsTo', [])

        return cat

    def get_collection(self, collection_id: str) -> CollectionClient:
        """Get a single collection from this Catalog/API

        Args:
            collection_id: The Collection ID to get

        Returns:
            CollectionClient: A STAC Collection
        """
        for col in self.get_collections():
            if col.id == collection_id:
                return col

    def get_collections(self) -> Iterable[CollectionClient]:
        """ Get Collections in this Catalog

            Gets the collections from the /collections endpoint if supported, otherwise fall
            back to Catalog behavior of following child links

        Return:
            Iterable[CollectionClient]: Iterator through Collections in Catalog/API
        """
        if self._stac_io.assert_conforms_to(ConformanceClasses.COLLECTIONS):
            url = self.get_self_href() + '/collections'
            for page in self._stac_io.get_pages(url):
                if 'collections' not in page:
                    raise APIError("Invalid response from /collections")
                for col in page['collections']:
                    collection = CollectionClient.from_dict(col, root=self)
                    yield collection
        else:
            yield from super().get_collections()

    def get_items(self) -> Iterable["Item_Type"]:
        """Return all items of this catalog.

        Return:
            Iterable[Item]:: Generator of items whose parent is this catalog.
        """
        if self._stac_io.assert_conforms_to(ConformanceClasses.ITEM_SEARCH):
            search = self.search()
            yield from search.get_items()
        else:
            return super().get_items()

    def get_all_items(self) -> Iterable["Item_Type"]:
        """Get all items from this catalog and all subcatalogs. Will traverse
        any subcatalogs recursively, or use the /search endpoint if supported

        Returns:
            Iterable[Item]:: All items that belong to this catalog, and all
                catalogs or collections connected to this catalog through
                child links.
        """
        if self._stac_io.assert_conforms_to(ConformanceClasses.ITEM_SEARCH):
            yield from self.get_items()
        else:
            yield from super().get_items()

    def search(self, **kwargs: Any) -> ItemSearch:
        """Query the ``/search`` endpoint using the given parameters.

        This method returns an :class:`~pystac_client.ItemSearch` instance, see that class's documentation
        for details on how to get the number of matches and iterate over results. All keyword arguments are passed
        directly to the :class:`~pystac_client.ItemSearch` instance.

        .. warning::

            This method is only implemented if the API conforms to the
            `STAC API - Item Search <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__ spec
            *and* contains a link with a ``"rel"`` type of ``"search"`` in its root catalog.
            If the API does not meet either of these criteria, this method will raise a :exc:`NotImplementedError`.

        Args:
            **kwargs : Any parameter to the :class:`~pystac_client.ItemSearch` class, other than `url`, `conformance`,
                and `stac_io` which are set from this Client instance

        Returns:
            search : An ItemSearch instance that can be used to iterate through Items.

        Raises:
            NotImplementedError: If the API does not conform to the `Item Search spec
                <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__ or does not have a link with
                a ``"rel"`` type of ``"search"``.
        """

        search_link = self.get_single_link('search')
        if search_link is None:
            raise NotImplementedError(
                'No link with "rel" type of "search" could be found in this catalog')

        return ItemSearch(search_link.target, stac_io=self._stac_io, client=self, **kwargs)
