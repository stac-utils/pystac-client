from typing import TYPE_CHECKING, Iterator, Optional, cast

import pystac

from pystac_client.conformance import ConformanceClasses
from pystac_client.exceptions import APIError
from pystac_client.item_search import ItemSearch
from pystac_client.stac_api_io import StacApiIO

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type


class CollectionClient(pystac.Collection):
    def __repr__(self) -> str:
        return "<CollectionClient id={}>".format(self.id)

    def get_items(self) -> Iterator["Item_Type"]:
        """Return all items in this Collection.

        If the Collection contains a link of with a `rel` value of `items`,
        that link will be used to iterate through items. Otherwise, the default
        PySTAC behavior is assumed.

        Return:
            Iterator[Item]: Iterator of items whose parent is this catalog.
        """

        link = self.get_single_link("items")
        root = self.get_root()
        if link is not None and root is not None:
            search = ItemSearch(
                url=link.href, method="GET", stac_io=root._stac_io  # type: ignore
            )
            yield from search.items()
        else:
            yield from super().get_items()

    def get_item(self, id: str, recursive: bool = False) -> Optional["Item_Type"]:
        """Returns an item with a given ID.

        If the collection conforms to
        [ogcapi-features](https://github.com/radiantearth/stac-api-spec/blob/738f4837ac6bea041dc226219e6d13b2c577fb19/ogcapi-features/README.md),
        this will use the `/collections/{collectionId}/items/{featureId}`.
        Otherwise, the default PySTAC behavior is used.

        Args:
            id : The ID of the item to find.
            recursive : If True, search this catalog and all children for the
                item; otherwise, only search the items of this catalog. Defaults
                to False.

        Return:
            Item or None: The item with the given ID, or None if not found.
        """
        if not recursive:
            root = self.get_root()
            assert root
            stac_io = root._stac_io
            assert stac_io
            assert isinstance(stac_io, StacApiIO)
            link = self.get_single_link("items")
            if stac_io.conforms_to(ConformanceClasses.FEATURES) and link is not None:
                url = f"{link.href}/{id}"
                try:
                    item = stac_io.read_stac_object(url, root=self)
                except APIError as err:
                    if err.status_code and err.status_code == 404:
                        return None
                    else:
                        raise err
                assert isinstance(item, pystac.Item)
                return item
            else:
                return super().get_item(id, recursive=False)
        else:
            for root, _, _ in self.walk():
                item = cast(pystac.Item, root.get_item(id, recursive=False))
                if item is not None:
                    assert isinstance(item, pystac.Item)
                    return item
            return None
