from pystac_client import CollectionClient

from .helpers import STAC_URLS


class TestCollectionClient:
    def test_instance(self):
        CollectionClient.from_file(STAC_URLS['PLANETARY-COMPUTER'] + '/collections/aster-l1t')
