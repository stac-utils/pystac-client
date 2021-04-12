from copy import deepcopy

import pystac

from pystac_client.stac_api_object import STACAPIObjectMixin


class ItemCollection(pystac.STACObject, STACAPIObjectMixin):
    """Implementation of the `STAC API ItemCollection Fragment
    <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/itemcollection>`__.

    Attributes
    ----------
    features : list
        A list of :class:`pystac.Item` instances for this instance.

    conformance : list
        A list of conformance URIs describing the specifications that this services conforms to. Note that this is
        not published as part of the `ItemCollection Fragment
        <https://github.com/radiantearth/stac-api-spec/blob/master/fragments/itemcollection/README.md>`__ itself and
        must be passed to one of the constructor methods.

    stac_extensions : list
        A list of STAC extensions that the instance implements. These apply to `static extensions
        <https://github.com/radiantearth/stac-spec/tree/master/extensions>`__ only and not
        `API extensions <https://github.com/radiantearth/stac-api-spec/blob/master/extensions.md>`__ as described in
        the `ItemCollection Fragment: Item Collection fields
        <https://github.com/radiantearth/stac-api-spec/blob/master/fragments/itemcollection/README.md#itemcollection-fields>`__
        docs.


    """
    def __init__(self, features=None, stac_extensions=None, conformance=None, extra_fields=None):
        super().__init__(stac_extensions)

        features = features or []
        self.features = [f.clone() for f in features]
        self.conformance = conformance or []
        self.extra_fields = extra_fields or {}

    def _object_links(self):
        return []

    def to_dict(self, include_self_link=True):
        """Serializes an :class:`ItemCollection` instance to a JSON-like dictionary. """

        links = self.links
        if not include_self_link:
            links = filter(lambda l: l.rel != 'self', links)

        d = {
            'type': 'FeatureCollection',
            'stac_version': pystac.get_stac_version(),
            'links': [link.to_dict() for link in links],
            'features': [f.to_dict() for f in self.features],
            **deepcopy(self.extra_fields)
        }

        if self.stac_extensions is not None:
            d['stac_extensions'] = self.stac_extensions

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
        """Parses a :class:`ItemCollection` instance from a dictionary. Note that ItemCollection objects do not publish
        their own conformance URIs in a "conformsTo" attribute. To add conformance URIs to indicate which API
        extensions an :class:`ItemCollection` instance implements you MUST pass this list in using the ``conformance``
        argument. See the :meth:`API.search <pystac_client.API.search>` method for an example."""
        d = deepcopy(d)

        features = [pystac.Item.from_dict(feature) for feature in d.pop('features', [])]
        links = d.pop('links', [])
        stac_extensions = d.pop('stac_extensions', None)

        item_collection = cls(features=features,
                              stac_extensions=stac_extensions,
                              extra_fields=deepcopy(d),
                              conformance=conformance)

        for link in links:
            item_collection.add_link(pystac.Link.from_dict(link))

        return item_collection
