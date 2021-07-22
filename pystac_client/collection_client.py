import pystac

from pystac_client.conformance import ConformanceMixin


class CollectionClient(pystac.Collection, ConformanceMixin):
    def __repr__(self):
        return '<CollectionClient id={}>'.format(self.id)

    @classmethod
    def from_dict(cls, *args, **kwargs) -> "CollectionClient":
        """

        """
        cat = super().from_dict(*args, **kwargs)

        return cat
