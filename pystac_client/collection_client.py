import pystac

from pystac_client.conformance import ConformanceMixin


class CollectionClient(pystac.Collection, ConformanceMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return '<CollectionClient id={}>'.format(self.id)
