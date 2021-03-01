import pystac
import pytest

from pystac_api import API, ConformanceClasses
from pystac_api.exceptions import ConformanceError

from .helpers import ASTRAEA_URL, read_data_file


class TestAPI:

    def test_instance(self):
        api_content = read_data_file('astraea_api.json', parse_json=True)
        api = API.from_dict(api_content)

        # An API instance is also a Catalog instance
        assert isinstance(api, pystac.Catalog)

        assert str(api) == '<API id=astraea>'

    @pytest.mark.vcr
    def test_links(self):
        api_content = read_data_file('astraea_api.json', parse_json=True)
        api = API.from_dict(api_content)

        # Should be able to get collections via links as with a typical PySTAC Catalog
        collection_links = api.get_links('child')
        assert len(collection_links) > 0

        first_collection = api.get_single_link('child').resolve_stac_object(root=api).target
        assert isinstance(first_collection, pystac.Collection)

    def test_spec_conformance(self):
        """Testing conformance against a ConformanceClass should allow APIs using legacy URIs to pass."""
        api_content = read_data_file('astraea_api.json', parse_json=True)

        # Set conformsTo URIs to conform with STAC API - Core using official URI
        api_content['conformsTo'] = [
            'https://api.stacspec.org/v1.0.0-beta.1/core'
        ]
        api = API.from_dict(api_content)

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
        api_content['conformsTo'] = [
            'http://stacspec.org/spec/api/1.0.0-beta.1/core'
        ]
        api = API.from_dict(api_content)

        # Must have a conformance property that is the list of URIs from the conformsTo property
        assert hasattr(api, 'conformance')
        assert api.conformance == api_content['conformsTo']

        assert api.conforms_to(ConformanceClasses.STAC_API_CORE)

        assert not api.conforms_to('https://api.stacspec.org/v1.0.0-beta.1/core')

    @pytest.mark.vcr
    def test_no_conformance(self):
        """Should raise a KeyError if no conformance info can be found. Luckily, the test API doesn't publish
        a "conformance" link so we can just remove the "conformsTo" attribute to test this."""
        api_content = read_data_file('astraea_api.json', parse_json=True)

        # Remove "conformsTo" attribute
        del api_content['conformsTo']

        with pytest.raises(KeyError):
            API.from_dict(api_content)

    @pytest.mark.vcr
    def test_no_stac_core_conformance(self):
        """Should raise a ConformanceError if the API does not conform to the STAC API - Core spec."""
        api_content = read_data_file('astraea_api.json', parse_json=True)

        # Remove "conformsTo" attribute
        api_content['conformsTo'] = []

        with pytest.raises(ConformanceError):
            API.from_dict(api_content)

    @pytest.mark.vcr
    def test_from_file(self):
        api = API.from_file(ASTRAEA_URL)

        assert api.title == 'Astraea Earth OnDemand'
