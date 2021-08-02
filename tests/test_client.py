from datetime import datetime

from dateutil.tz import tzutc
import pystac
import pytest

from pystac_client import Client
from pystac_client.conformance import ConformanceClasses

from .helpers import STAC_URLS, TEST_DATA


class TestAPI:
    @pytest.mark.vcr
    def test_instance(self):
        api = Client.open(STAC_URLS['PLANETARY-COMPUTER'])

        # An API instance is also a Catalog instance
        assert isinstance(api, pystac.Catalog)

        assert str(api) == '<Client id=microsoft-pc>'

    @pytest.mark.vcr
    def test_links(self):
        api = Client.open(STAC_URLS['PLANETARY-COMPUTER'])

        # Should be able to get collections via links as with a typical PySTAC Catalog
        collection_links = api.get_links('child')
        assert len(collection_links) > 0

        collections = list(api.get_collections())
        assert len(collection_links) == len(collections)

        first_collection = api.get_single_link('child').resolve_stac_object(root=api).target
        assert isinstance(first_collection, pystac.Collection)

    def test_spec_conformance(self):
        """Testing conformance against a ConformanceClass should allow APIs using legacy URIs to pass."""
        client = Client.from_file(str(TEST_DATA / 'planetary-computer-root.json'))

        # Set conformsTo URIs to conform with STAC API - Core using official URI
        client._stac_io._conformance = ['https://api.stacspec.org/v1.0.0-beta.1/core']

        assert client.assert_conforms_to(ConformanceClasses.CORE)

    @pytest.mark.vcr
    def test_no_conformance(self):
        """Should raise a NotImplementedError if no conformance info can be found. Luckily, the test API doesn't publish
        a "conformance" link so we can just remove the "conformsTo" attribute to test this."""
        client = Client.from_file(str(TEST_DATA / 'planetary-computer-root.json'))
        client._stac_io._conformance = []

        with pytest.raises(NotImplementedError):
            client.assert_conforms_to(ConformanceClasses.CORE)

        with pytest.raises(NotImplementedError):
            client.assert_conforms_to(ConformanceClasses.ITEM_SEARCH)

    @pytest.mark.vcr
    def test_no_stac_core_conformance(self):
        """Should raise a NotImplementedError if the API does not conform to the STAC API - Core spec."""
        client = Client.from_file(str(TEST_DATA / 'planetary-computer-root.json'))
        client._stac_io._conformance = client._stac_io._conformance[1:]

        with pytest.raises(NotImplementedError):
            client.assert_conforms_to(ConformanceClasses.CORE)

        assert client.assert_conforms_to(ConformanceClasses.ITEM_SEARCH)

    @pytest.mark.vcr
    def test_from_file(self):
        api = Client.from_file(STAC_URLS['PLANETARY-COMPUTER'])

        assert api.title == 'Microsoft Planetary Computer STAC API'

    def test_invalid_url(self):
        with pytest.raises(TypeError):
            Client.open()


class TestAPISearch:
    @pytest.fixture(scope='function')
    def api(self):
        return Client.from_file(str(TEST_DATA / 'planetary-computer-root.json'))

    def test_search_conformance_error(self, api):
        """Should raise a NotImplementedError if the API doesn't conform to the Item Search spec. Message should
        include information about the spec that was not conformed to."""
        # Set the conformance to only STAC API - Core
        api._stac_io._conformance = [api._stac_io._conformance[0]]

        with pytest.raises(NotImplementedError) as excinfo:
            api.search(limit=10, max_items=10, collections='mr-peebles')
        assert str(ConformanceClasses.ITEM_SEARCH) in str(excinfo.value)

    def test_no_search_link(self, api):
        # Remove the search link
        api.remove_links('search')

        with pytest.raises(NotImplementedError) as excinfo:
            api.search(limit=10, max_items=10, collections='naip')
        assert 'No link with "rel" type of "search"' in str(excinfo.value)

    def test_search(self, api):
        results = api.search(bbox=[-73.21, 43.99, -73.12, 44.05],
                             collections='naip',
                             limit=10,
                             max_items=20,
                             datetime=[datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzutc()), None])

        assert results._parameters == {
            'bbox': (-73.21, 43.99, -73.12, 44.05),
            'collections': ('naip', ),
            'limit': 10,
            'datetime': '2020-01-01T00:00:00Z/..'
        }
