from datetime import datetime
import os

from dateutil.tz import tzutc
import pystac
import pytest

from pystac_client import Client
from pystac_client.conformance import ConformanceClasses

from .helpers import STAC_URLS, TEST_DATA, read_data_file


class TestAPI:
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

        collection_links_alt = api.get_collections_list()
        assert len(collection_links) == len(collection_links_alt)

        first_collection = api.get_single_link('child').resolve_stac_object(root=api).target
        assert isinstance(first_collection, pystac.Collection)

    def test_spec_conformance(self):
        """Testing conformance against a ConformanceClass should allow APIs using legacy URIs to pass."""
        api_content = read_data_file('planetary-computer-root.json', parse_json=True)

        # Set conformsTo URIs to conform with STAC API - Core using official URI
        api_content['conformsTo'] = ['https://api.stacspec.org/v1.0.0-beta.1/core']
        api = Client.from_dict(api_content)

        # Must have a conformance property that is the list of URIs from the conformsTo property
        assert hasattr(api, 'conformance')
        assert api.conformance == api_content['conformsTo']
        # Check the conformance to STAC API - Core using the ConformanceClass

        assert api.conforms_to(ConformanceClasses.CORE)

    @pytest.mark.vcr
    def test_no_conformance(self):
        """Should raise a NotImplementedError if no conformance info can be found. Luckily, the test API doesn't publish
        a "conformance" link so we can just remove the "conformsTo" attribute to test this."""
        api_content = read_data_file('planetary-computer-root.json', parse_json=True)

        # Set to no conformance
        api_content['conformsTo'] = []

        with pytest.raises(NotImplementedError):
            Client.from_dict(api_content)

    @pytest.mark.vcr
    def test_no_stac_core_conformance(self):
        """Should raise a NotImplementedError if the API does not conform to the STAC API - Core spec."""
        api_content = read_data_file('planetary-computer-root.json', parse_json=True)

        # Remove "conformsTo" attribute
        api_content['conformsTo'] = []

        with pytest.raises(NotImplementedError):
            Client.from_dict(api_content)

    @pytest.mark.vcr
    def test_from_file(self):
        api = Client.from_file(STAC_URLS['PLANETARY-COMPUTER'])

        assert api.title == 'Microsoft Planetary Computer STAC API'

    @pytest.mark.vcr
    def test_environment_variable(self):
        old_stac_url = os.environ.get("STAC_URL")
        os.environ["STAC_URL"] = STAC_URLS['PLANETARY-COMPUTER']
        try:
            client = Client.open()
            assert client.title == "Microsoft Planetary Computer STAC API"
        finally:
            if old_stac_url:
                os.environ["STAC_URL"] = old_stac_url
            else:
                del os.environ["STAC_URL"]

    def test_no_url(self):
        old_stac_url = os.environ.get("STAC_URL")
        if old_stac_url:
            del os.environ["STAC_URL"]
        try:
            with pytest.raises(TypeError):
                Client.open()
        finally:
            if old_stac_url:
                os.environ["STAC_URL"] = old_stac_url


class TestAPISearch:
    @pytest.fixture(scope='function')
    def api(self):
        return Client.from_file(str(TEST_DATA / 'planetary-computer-root.json'))

    def test_search_conformance_error(self, api):
        """Should raise a NotImplementedError if the API doesn't conform to the Item Search spec. Message should
        include information about the spec that was not conformed to."""
        # Set the conformance to only STAC API - Core
        api.conformance = [api.conformance[0]]

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
