import pytest
from pystac.extensions import ExtensionError

from pystac_client import Client, APIExtensions, ConformanceClasses

from .helpers import ASTRAEA_API_PATH


class TestAPIExtensionIndex:
    @pytest.fixture(scope='function')
    def api(self):
        return Client.from_file(ASTRAEA_API_PATH)

    def test_implements_api_ext(self, api):
        api.conformance = [
            ConformanceClasses.STAC_API_CORE.uri, ConformanceClasses.STAC_API_ITEM_SEARCH.uri,
            ConformanceClasses.STAC_API_ITEM_SEARCH_CONTEXT_EXT.uri
        ]

        assert api.api_ext.implements(APIExtensions.CONTEXT) is True
        assert api.api_ext.implements('not_an_extension') is False

    def test_get_extension(self, api):
        api.conformance = [
            ConformanceClasses.STAC_API_CORE.uri, ConformanceClasses.STAC_API_ITEM_SEARCH.uri,
            ConformanceClasses.STAC_API_ITEM_SEARCH_CONTEXT_EXT.uri
        ]

        try:
            api.api_ext.context
        except Exception as e:
            pytest.fail(f'Failed to get extension from attribute: {e}')

        try:
            api.api_ext['context']
        except Exception as e:
            pytest.fail(f'Failed to get extension from dictionary key: {e}')

        with pytest.raises(ExtensionError) as excinfo:
            api.api_ext['not_an_extension']

        assert 'is not an extension registered with pystac-client' in str(excinfo.value)
