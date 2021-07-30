from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    TYPE_CHECKING,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import pystac
from pystac_client.conformance import ConformanceClasses
from pystac_client.item_search import ItemSearch

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type
    from pystac.catalog import Catalog as Catalog_Type


class CollectionClient(pystac.Collection):
    def __repr__(self):
        return '<CollectionClient id={}>'.format(self.id)

    def conforms_to(self, conformance: ConformanceClasses) -> bool:
        return self._stac_io.conforms_to(conformance)

    @classmethod
    def from_dict(cls, *args, root: Optional["Catalog_Type"] = None, **kwargs):
        col = super().from_dict(*args, **kwargs)
        if root is not None:
            col._stac_io = root._stac_io
        return col

    def get_items(self) -> Iterable["Item_Type"]:
        if self.conforms_to(ConformanceClasses.COLLECTIONS):
            url = f"{self.get_root_link()}/collections/{self.id}/items"
            breakpoint()

