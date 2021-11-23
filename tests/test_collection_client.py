from urllib.parse import urlsplit, parse_qs
import pytest

from pystac_client import CollectionClient
from pystac_client.client import Client

from .helpers import STAC_URLS, read_data_file


class TestCollectionClient:
    @pytest.mark.vcr
    def test_instance(self):
        client = Client.open(STAC_URLS['PLANETARY-COMPUTER'])
        collection = client.get_collection('aster-l1t')

        assert isinstance(collection, CollectionClient)
        assert str(collection) == '<CollectionClient id=aster-l1t>'

    @pytest.mark.vcr
    def test_get_items(self):
        client = Client.open(STAC_URLS['PLANETARY-COMPUTER'])
        collection = client.get_collection('aster-l1t')
        for item in collection.get_items():
            assert (item.collection_id == collection.id)
            return

    def test_custom_query_params(self, requests_mock):
        """Checks that query params passed to the init method are added to requests."""
        pc_root_text = read_data_file("planetary-computer-root.json")
        pc_collection_dict = read_data_file("planetary-computer-collection.json", parse_json=True)

        requests_mock.get(STAC_URLS["PLANETARY-COMPUTER"], status_code=200, text=pc_root_text)

        init_qp_name = "my-param"
        init_qp_value = "some-value"

        client = Client.open(STAC_URLS['PLANETARY-COMPUTER'], parameters={init_qp_name: init_qp_value})

        # Get the /collections endpoint
        collections_link = client.get_single_link("data")

        # Mock the request
        requests_mock.get(collections_link.href,
                          status_code=200,
                          json={
                              "collections": [pc_collection_dict],
                              "links": []
                          })

        # Make the collections request
        collection = next(client.get_collections())

        # Mock the items endpoint
        items_link = collection.get_single_link('items')
        assert items_link is not None
        requests_mock.get(items_link.href, status_code=200, json={"type": "FeatureCollection", "stac_version": "1.0.0", "features": [], "links": []})

        # Make the items request
        _ = list(collection.get_items())

        history = requests_mock.request_history
        assert len(history) == 3

        actual_qs = urlsplit(history[2].url).query
        actual_qp = parse_qs(actual_qs)

        # Check that the query param from the root Client is present
        assert init_qp_name in actual_qp
        assert len(actual_qp[init_qp_name]) == 1
        assert actual_qp[init_qp_name][0] == init_qp_value
