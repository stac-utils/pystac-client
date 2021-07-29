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

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type
    from pystac.catalog import Catalog as Catalog_Type


class CollectionClient(pystac.Collection):
    def __repr__(self):
        return '<CollectionClient id={}>'.format(self.id)

    #def get_items(self) -> Iterable["Item_Type"]:
    #    if self.conforms_to(ConformanceClasses.COLLECTIONS):

