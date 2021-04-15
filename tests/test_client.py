from datetime import datetime

from dateutil.tz import tzutc
import pystac
import pytest

from pystac_client import Client, ConformanceClasses
from pystac_client.exceptions import ConformanceError

from .helpers import ASTRAEA_API_PATH, ASTRAEA_URL, TEST_DATA, read_data_file


class TestAPI:
    def test_instance(self):
        api = Client.from_file(ASTRAEA_API_PATH)

        # An API instance is also a Catalog instance
        assert isinstance(api, pystac.Catalog)

        assert str(api) == '<Catalog id=astraea>'

    @pytest.mark.vcr
    def test_links(self):
        api = Client.from_file(ASTRAEA_API_PATH)

        # Should be able to get collections via links as with a typical PySTAC Catalog
        collection_links = api.get_links('child')
        assert len(collection_links) > 0

        first_collection = api.get_single_link('child').resolve_stac_object(root=api).target
        assert isinstance(first_collection, pystac.Collection)

    def test_spec_conformance(self):
        """Testing conformance against a ConformanceClass should allow APIs using legacy URIs to pass."""
        api_content = read_data_file('astraea_api.json', parse_json=True)

        # Set conformsTo URIs to conform with STAC API - Core using official URI
        api_content['conformsTo'] = ['https://api.stacspec.org/v1.0.0-beta.1/core']
        api = Client.from_dict(api_content)

        # Must have a conformance property that is the list of URIs from the conformsTo property
        assert hasattr(api, 'conformance')
        assert api.conformance == api_content['conformsTo']

        # Check the conformance to STAC API - Core using the ConformanceClass
        assert api.conforms_to(ConformanceClasses.STAC_API_CORE)

        # ... and using a URI string
        assert api.conforms_to('https://api.stacspec.org/v1.0.0-beta.1/core')

    def test_legacy_conformance(self):
        """APIs publishing legacy conformance URIs should pass when tested against a ConformanceClass, but
        fail when tested against the official URI string"""
        api_content = read_data_file('astraea_api.json', parse_json=True)

        # Set conformsTo URIs to conform with STAC API - Core using official URI
        api_content['conformsTo'] = ['http://stacspec.org/spec/api/1.0.0-beta.1/core']
        api = Client.from_dict(api_content)

        # Must have a conformance property that is the list of URIs from the conformsTo property
        assert hasattr(api, 'conformance')
        assert api.conformance == api_content['conformsTo']

        assert api.conforms_to(ConformanceClasses.STAC_API_CORE)

        assert not api.conforms_to('https://api.stacspec.org/v1.0.0-beta.1/core')

    @pytest.mark.skip(reason="Conformance testing has been loosened to accommodate legacy services."
                      )
    @pytest.mark.vcr
    def test_no_conformance(self):
        """Should raise a KeyError if no conformance info can be found. Luckily, the test API doesn't publish
        a "conformance" link so we can just remove the "conformsTo" attribute to test this."""
        api_content = read_data_file('astraea_api.json', parse_json=True)

        # Remove "conformsTo" attribute
        del api_content['conformsTo']

        with pytest.raises(KeyError):
            Client.from_dict(api_content)

    @pytest.mark.vcr
    def test_no_stac_core_conformance(self):
        """Should raise a ConformanceError if the API does not conform to the STAC API - Core spec."""
        api_content = read_data_file('astraea_api.json', parse_json=True)

        # Remove "conformsTo" attribute
        api_content['conformsTo'] = []

        with pytest.raises(ConformanceError):
            Client.from_dict(api_content)

    @pytest.mark.vcr
    def test_from_file(self):
        api = Client.from_file(ASTRAEA_URL)

        assert api.title == 'Astraea Earth OnDemand'


class TestAPISearch:
    @pytest.fixture(scope='function')
    def api(self):
        return Client.from_file(str(TEST_DATA / 'astraea_api.json'))

    def test_search_conformance_error(self, api):
        """Should raise a NotImplementedError if the API doesn't conform to the Item Search spec. Message should
        include information about the spec that was not conformed to."""
        # Set the conformance to only STAC API - Core
        api.conformance = [ConformanceClasses.STAC_API_CORE.uri]

        with pytest.raises(NotImplementedError) as excinfo:
            api.search(limit=10, max_items=10, collections='naip')

        assert ConformanceClasses.STAC_API_ITEM_SEARCH.name in str(excinfo.value)
        assert all(uri in str(excinfo.value)
                   for uri in ConformanceClasses.STAC_API_ITEM_SEARCH.all_uris)

    def test_no_search_link(self, api):
        # Remove the search link
        api.remove_links('search')

        with pytest.raises(NotImplementedError) as excinfo:
            api.search(limit=10, max_items=10, collections='naip')

        assert 'No link with a "rel" type of "search"' in str(excinfo.value)

    def test_search(self, api):
        results = api.search(bbox=[-73.21, 43.99, -73.12, 44.05],
                             collections='naip',
                             limit=10,
                             max_items=20,
                             datetime=[datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzutc()), None])

        assert results.request.json == {
            'bbox': (-73.21, 43.99, -73.12, 44.05),
            'collections': ('naip', ),
            'limit': 10,
            'datetime': '2020-01-01T00:00:00Z/..'
        }
