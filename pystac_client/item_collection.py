import json
# from copy import deepcopy
from typing import Any, Dict, List, Optional

from pystac.item import Item
from pystac.layout import LayoutTemplate
from pystac.link import Link


class ItemCollection(object):
    """Implementation of the `STAC API ItemCollection Fragment
    <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/itemcollection>`__.

    Attributes
    ----------
    features : list
        A list of :class:`pystac.Item` objects.
    """
    def __init__(
        self,
        features: List[Item],
        links: List[Link] = [],
        extra_fields: Optional[Dict[str, Any]] = {},
    ):
        features = features or []
        self.features = [f.clone() for f in features]
        self.extra_fields = extra_fields
        self.links = links
        for f in self.features:
            f.clear_links('root')

    def __getitem__(self, key):
        return self.features[key]

    def to_dict(self, include_self_link=True):
        """Serializes an :class:`ItemCollection` instance to a JSON-like dictionary. """

        links = self.links
        if not include_self_link:
            links = filter(lambda l: l.rel != 'self', links)

        d = {
            'type': 'FeatureCollection',
            'links': [link.to_dict() for link in links],
            'features': [f.to_dict() for f in self.features]
        }

        return d

    def add_link(self, link: Link) -> None:
        """Add a link to this object's set of links.

        Args:
             link : The link to add.
        """
        self.links.append(link)

    def add_links(self, links: List[Link]) -> None:
        """Add links to this object's set of links.

        Args:
             links : The links to add.
        """
        for link in links:
            self.add_link(link)

    def get_fields(self, fields=[]):
        field_str = '/'.join([f"${{{f}}}" for f in fields])
        layout = LayoutTemplate(field_str)
        data = [layout.substitute(f).split('/') for f in self.features]
        return data

    def clone(self):
        """Creates a clone of this object. This clone is a deep copy; all links are cloned and all other
         elements are copied (for shallow lists) or deep copied (for dictionaries)."""
        clone = self.__class__(features=[item.clone() for item in self.features],
                               collections=[item.get_collection() for item in self.features])
        for link in self.links:
            clone.add_link(link.clone())
        return clone

    @classmethod
    def from_dict(cls, d):
        """Parses this STACObject from the passed in dictionary.

        Args:
            d : The dict to parse
        """
        features = [Item.from_dict(feature) for feature in d.pop('features', [])]

        links = []
        for link in d.pop('links', []):
            links.append(Link.from_dict(link))

        item_collection = cls(features=features, links=links, extra_fields=d)

        return item_collection

    @classmethod
    def from_file(cls, filename: str):
        """Reads an ItemCollection implementation from a file.

        Args:
            href : The HREF to read the object from.
            stac_io: Optional instance of StacIO to use. If not provided, will use the
                default instance.

        Returns:
            The specific STACObject implementation class that is represented
            by the JSON read from the file located at HREF.
        """
        with open(filename) as f:
            return cls.from_dict(json.loads(f.read()))
