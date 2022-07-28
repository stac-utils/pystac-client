from typing import Union

import pystac

Modifiable = Union[pystac.Collection, pystac.Item, pystac.ItemCollection, dict]


def no_modifier(x: Modifiable) -> None:
    pass
