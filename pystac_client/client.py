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
    """Instances of the ``Client`` class inherit from :class:`pystac.Catalog` and provide a convenient way of interacting
    with STAC Catalogs OR STAC APIs that conform to the `STAC API spec <https://github.com/radiantearth/stac-api-spec>`_.
    In addition to being a valid
    `STAC Catalog <https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/catalog-spec.md>`_
    APIs that have a ``"conformsTo"`` indicate that it supports additional functionality on top of a normal STAC Catalog,
    such as searching items (e.g., /search endpoint).

    PySTAC Client works by defining a new StacIO class to define how the catalog is read and supports HTTP API endpoints.
    The preferred way to initially open a catalog/API as a Client is to use the ``open`` function. This calls the PySTAC
    ``from_file`` function. Some functions, such as ``Client.search`` will throw an error if the provided Catalog/API does
    not support the required Conformance Class. In other cases, such as ``Client.get_collections``, API endpoints will be
    used if the API conforms, otherwise it will fall back to default behavior provided by :class:`pystac.Catalog`.

    Users may optionally provide an ``ignore_conformance`` argument when opening, in which case pystac-client will not check
    for conformance and will assume this is a fully features API. This can cause unusual errors to be thrown if the API
    does not in fact conform to the expected behavior.

    In addition to the methods and attributes inherited from :class:`pystac.Catalog`, this class offers more efficient
    methods (if used with an API) for getting collections and items, as well as a search capability, utilizing the
    :class:`pystac_client.ItemSearch` class.
    """
    def __repr__(self):
        return '<Client id={}>'.format(self.id)

    @classmethod
    def open(cls, url, headers=None, ignore_conformance: bool = False):
        """Alias for PySTAC's STAC Object `from_file` method

        Parameters
        ----------
        url : str, optional
            The URL of a STAC Catalog. If not specified, this will use the `STAC_URL` environment variable.
        headers : Dict[str, str]
            A dictionary of additional headers to use in all requests made to any part of this Catalog/API.

        ignore_conformance : bool
            Ignore any advertised Conformance Classes in this Catalog/API. This means that pystac-client will attempt
            to use API features regardless and not throw a :class:`NotImplementedError`.

        Returns
        -------
        catalog : Client
            An instance of :class:`Client`, which acts as a normal :class:`pystac.Catalog` for static Catalogs.
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
        if stac_io is None:
            stac_io = StacApiIO(headers=headers)

        cat = super().from_file(href, stac_io)

        cat._stac_io._conformance = cat.extra_fields.get('conformsTo', [])

        return cat

    def assert_conforms_to(self, conformance: ConformanceClasses) -> bool:
        return self._stac_io.assert_conforms_to(conformance)

    def get_collection(self, collection_id) -> Iterable[CollectionClient]:
        for col in self.get_collections():
            if col.id == collection_id:
                return col

    def get_collections(self) -> Iterable[CollectionClient]:
        """ Get Collections from the /collections endpoint if supported, otherwise fall
            back to Catalog behavior of following child links """
        if self.assert_conforms_to(ConformanceClasses.COLLECTIONS):
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
            Iterable[Item]: Generator of items whose parent is this catalog.
        """
        if self.assert_conforms_to(ConformanceClasses.ITEM_SEARCH):
            search = self.search()
            yield from search.get_items()
        else:
            return super().get_items()

    def get_all_items(self) -> Iterable["Item_Type"]:
        """Get all items from this catalog and all subcatalogs. Will traverse
        any subcatalogs recursively, or use the /search endpoint if supported

        Returns:
            Generator[Item]: All items that belong to this catalog, and all
                catalogs or collections connected to this catalog through
                child links.
        """
        if self.assert_conforms_to(ConformanceClasses.ITEM_SEARCH):
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

        Parameters
        ----------
        **kwargs : Any pameter to the ItemSearch class, other than `url`, `conformance`, and `stac_io` which are set
        from this Client instance

        Returns
        -------
        results : ItemSearch

        Raises
        ------
        NotImplementedError
            If the API does not conform to the `Item Search spec
            <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__ or does not have a link with
            a ``"rel"`` type of ``"search"``.
        """

        search_link = self.get_single_link('search')
        if search_link is None:
            raise NotImplementedError(
                'No link with "rel" type of "search" could be found in this catalog')

        return ItemSearch(search_link.target, stac_io=self._stac_io, client=self, **kwargs)
