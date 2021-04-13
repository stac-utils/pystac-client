import json
from copy import deepcopy

import pystac


class ItemCollection(object):
    """Implementation of the `STAC API ItemCollection Fragment
    <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/itemcollection>`__.

    Attributes
    ----------
    features : list
        A list of :class:`pystac.Item` instances for this instance.

    """
    def __init__(self, features=None):
        super().__init__()

        features = features or []
        self.features = [f.clone() for f in features]
        self.links = []
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

    def clone(self):
        """Creates a clone of this object. This clone is a deep copy; all links are cloned and all other
         elements are copied (for shallow lists) or deep copied (for dictionaries)."""
        clone = self.__class__(features=[item.clone() for item in self.features],
                               stac_extensions=list(self.stac_extensions)
                               if self.stac_extensions is not None else None,
                               extra_fields=deepcopy(self.extra_fields),
                               conformance=list(self.conformance))
        for link in self.links:
            clone.add_link(link.clone())
        return clone

    @classmethod
    def from_dict(cls, d, conformance=None, href=None, root=None):
        """Parses a :class:`ItemCollection` instance from a dictionary. """
        features = [pystac.Item.from_dict(feature) for feature in d.pop('features', [])]

        item_collection = cls(features=features)

        return item_collection

    @classmethod
    def from_file(cls, filename):
        with open(filename) as f:
            return cls.from_dict(json.loads(f.read()))

    def save(self, filename):
        with open(filename, 'w') as f:
            f.write(json.dumps(self.to_dict()))
