from typing import (Iterable, Optional, TYPE_CHECKING)

import pystac
from pystac_client.conformance import ConformanceClasses
from pystac_client.item_search import ItemSearch

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type
    from pystac.catalog import Catalog as Catalog_Type


class CollectionClient(pystac.Collection):
    def __repr__(self):
        return '<CollectionClient id={}>'.format(self.id)

    def assert_conforms_to(self, conformance: ConformanceClasses) -> bool:
        return self._stac_io.conforms_to(conformance)

    @classmethod
    def from_dict(cls, *args, root: Optional["Catalog_Type"] = None, **kwargs):
        col = super().from_dict(*args, **kwargs)
        if root is not None:
            col._stac_io = root._stac_io
        return col

    def get_items(self) -> Iterable["Item_Type"]:
        if self.assert_conforms_to(ConformanceClasses.COLLECTIONS):
            url = f"{self.get_root_link().href}/collections/{self.id}/items"
            search = ItemSearch(url, method='GET')
            yield from search.get_items()
        else:
            yield from super().get_items()
