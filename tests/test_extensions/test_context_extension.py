import pytest

from pystac_client import APIExtensions, ConformanceClasses, ItemSearch

from ..helpers import ASTRAEA_URL


class TestItemCollectionContextExtension:
    @pytest.mark.vcr
    def test_context_matched(self):
        results = ItemSearch(url=f'{ASTRAEA_URL}/search',
                             bbox=[-73.3, 43.9, -73.1, 44.1],
                             collections='naip',
                             conformance=[
                                 ConformanceClasses.STAC_API_CORE,
                                 ConformanceClasses.STAC_API_ITEM_SEARCH,
                                 ConformanceClasses.STAC_API_ITEM_SEARCH_CONTEXT_EXT
                             ],
                             limit=12)

        first_item_collection = next(results.item_collections())
        assert first_item_collection.api_ext.implements(APIExtensions.CONTEXT)
        assert first_item_collection.api_ext.context.limit == 12
        assert first_item_collection.api_ext.context.returned == 12
