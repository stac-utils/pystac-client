import json
from datetime import datetime, timedelta

import pystac
import pytest
from dateutil.tz import gettz, tzutc

from pystac_api import API
from pystac_api.item_search import ItemSearch

from .helpers import ASTRAEA_URL, read_data_file


class TestItemSearch:
    """Use the API.search method instead of ItemSearch directly to make auth handling easier."""

    SEARCH_URL = f'{ASTRAEA_URL}/search'

    INTERSECTS_EXAMPLE = {
        'type': 'Polygon',
        'coordinates': [[
            [-73.21, 43.99],
            [-73.21, 44.05],
            [-73.12, 44.05],
            [-73.12, 43.99],
            [-73.21, 43.99]
        ]]
    }

    @pytest.fixture(scope='function')
    def astraea_api(self):
        api_content = read_data_file('astraea_api.json', parse_json=True)
        return API.from_dict(api_content)

    def test_method(self):
        # Default method should be GET...
        search = ItemSearch(url=ASTRAEA_URL)
        assert search.method == 'GET'

        # ...unless the "intersects" argument is present.
        search = ItemSearch(url=ASTRAEA_URL, intersects=TestItemSearch.INTERSECTS_EXAMPLE)
        assert search.method == 'POST'

        # "method" argument should take precedence over presence of "intersects"
        search = ItemSearch(url=ASTRAEA_URL, method='GET', intersects=TestItemSearch.INTERSECTS_EXAMPLE)
        assert search.method == 'GET'

    def test_bbox_param(self):
        # Tuple input
        search = ItemSearch(url=ASTRAEA_URL, bbox=(-104.5, 44.0, -104.0, 45.0))
        assert search.search_parameters_post['bbox'] == (-104.5, 44.0, -104.0, 45.0)

        # List input
        search = ItemSearch(url=ASTRAEA_URL, bbox=[-104.5, 44.0, -104.0, 45.0])
        assert search.search_parameters_post['bbox'] == (-104.5, 44.0, -104.0, 45.0)

        # String Input
        search = ItemSearch(url=ASTRAEA_URL, bbox='-104.5,44.0,-104.0,45.0')
        assert search.search_parameters_post['bbox'] == (-104.5, 44.0, -104.0, 45.0)

        # Generator Input
        def bboxer():
            yield from [-104.5, 44.0, -104.0, 45.0]

        search = ItemSearch(url=ASTRAEA_URL, bbox=bboxer())
        assert search.search_parameters_post['bbox'] == (-104.5, 44.0, -104.0, 45.0)

    def test_datetime_param(self):
        # Single timestamp input
        search = ItemSearch(url=ASTRAEA_URL, datetime='2020-02-01T00:00:00Z')
        assert search.search_parameters_post['datetime'] == ('2020-02-01T00:00:00Z',)

        # Timestamp range input
        search = ItemSearch(url=ASTRAEA_URL, datetime='2020-02-01T00:00:00Z/2020-02-02T00:00:00Z')
        assert search.search_parameters_post['datetime'] == ('2020-02-01T00:00:00Z', '2020-02-02T00:00:00Z')

        # Timestamp list input
        search = ItemSearch(url=ASTRAEA_URL, datetime=['2020-02-01T00:00:00Z', '2020-02-02T00:00:00Z'])
        assert search.search_parameters_post['datetime'] == ('2020-02-01T00:00:00Z', '2020-02-02T00:00:00Z')

        # Open timestamp range input
        search = ItemSearch(url=ASTRAEA_URL, datetime='2020-02-01T00:00:00Z/..')
        assert search.search_parameters_post['datetime'] == ('2020-02-01T00:00:00Z', '..')

        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())

        # Single datetime input
        search = ItemSearch(url=ASTRAEA_URL, datetime=start)
        assert search.search_parameters_post['datetime'] == ('2020-02-01T00:00:00Z',)

        # Datetime range input
        search = ItemSearch(url=ASTRAEA_URL, datetime=[start, end])
        assert search.search_parameters_post['datetime'] == ('2020-02-01T00:00:00Z', '2020-02-02T00:00:00Z')

        # Open datetime range input
        search = ItemSearch(url=ASTRAEA_URL, datetime=(start, None))
        assert search.search_parameters_post['datetime'] == ('2020-02-01T00:00:00Z', '..')

        # Localized datetime input (should be converted to UTC)
        start_localized = datetime(2020, 2, 1, 0, 0, 0, tzinfo=gettz('US/Eastern'))
        search = ItemSearch(url=ASTRAEA_URL, datetime=start_localized)
        assert search.search_parameters_post['datetime'] == ('2020-02-01T05:00:00Z',)

    @pytest.mark.vcr
    def test_collections_param(self, astraea_api):
        # Single ID string
        search = ItemSearch(url=ASTRAEA_URL, collections='naip')
        assert search.search_parameters_post['collections'] == ('naip',)

        # Comma-separated ID string
        search = ItemSearch(url=ASTRAEA_URL, collections='naip,landsat8_l1tp')
        assert search.search_parameters_post['collections'] == ('naip', 'landsat8_l1tp')

        # List of ID strings
        search = ItemSearch(url=ASTRAEA_URL, collections=['naip', 'landsat8_l1tp'])
        assert search.search_parameters_post['collections'] == ('naip', 'landsat8_l1tp')

        # Generator of ID strings
        def collectioner():
            yield from ['naip', 'landsat8_l1tp']
        search = ItemSearch(url=ASTRAEA_URL, collections=collectioner())
        assert search.search_parameters_post['collections'] == ('naip', 'landsat8_l1tp')

        collection = astraea_api.get_child('landsat8_l1tp')

        # Single pystac.Collection
        search = ItemSearch(url=ASTRAEA_URL, collections=collection)
        assert search.search_parameters_post['collections'] == ('landsat8_l1tp',)

        # Mixed list
        search = ItemSearch(url=ASTRAEA_URL, collections=[collection, 'naip'])
        assert search.search_parameters_post['collections'] == ('landsat8_l1tp', 'naip')

    def test_ids_param(self):
        # Single ID
        search = ItemSearch(url=ASTRAEA_URL, ids='m_3510836_se_12_060_20180508_20190331')
        assert search.search_parameters_post['ids'] == ('m_3510836_se_12_060_20180508_20190331',)

        # Comma-separated ID string
        search = ItemSearch(
            url=ASTRAEA_URL,
            ids='m_3510836_se_12_060_20180508_20190331,m_3510840_se_12_060_20180504_20190331'
        )
        assert search.search_parameters_post['ids'] == (
            'm_3510836_se_12_060_20180508_20190331',
            'm_3510840_se_12_060_20180504_20190331'
        )

        # List of IDs
        search = ItemSearch(
            url=ASTRAEA_URL,
            ids=[
                'm_3510836_se_12_060_20180508_20190331',
                'm_3510840_se_12_060_20180504_20190331'
            ]
        )
        assert search.search_parameters_post['ids'] == (
            'm_3510836_se_12_060_20180508_20190331',
            'm_3510840_se_12_060_20180504_20190331'
        )

        # Generator of IDs
        def ids():
            yield from [
                'm_3510836_se_12_060_20180508_20190331',
                'm_3510840_se_12_060_20180504_20190331'
            ]

        search = ItemSearch(
            url=ASTRAEA_URL,
            ids=ids()
        )
        assert search.search_parameters_post['ids'] == (
            'm_3510836_se_12_060_20180508_20190331',
            'm_3510840_se_12_060_20180504_20190331'
        )

    def test_intersects_param(self):
        # Dict input
        search = ItemSearch(url=TestItemSearch.SEARCH_URL, intersects=TestItemSearch.INTERSECTS_EXAMPLE)
        assert search.search_parameters_post['intersects'] == TestItemSearch.INTERSECTS_EXAMPLE

        # JSON string input
        search = ItemSearch(url=TestItemSearch.SEARCH_URL, intersects=json.dumps(TestItemSearch.INTERSECTS_EXAMPLE))
        assert search.search_parameters_post['intersects'] == TestItemSearch.INTERSECTS_EXAMPLE

    @pytest.mark.vcr
    def test_results(self):
        results = ItemSearch(
            url=TestItemSearch.SEARCH_URL,
            collections='naip',
            max_items=20,
            limit=10,
        )

        assert all(isinstance(item, pystac.Item) for item in results)

    @pytest.mark.vcr
    def test_ids_results(self):
        ids = [
            'm_3510836_se_12_060_20180508_20190331',
            'm_3510840_se_12_060_20180504_20190331'
        ]
        results = list(ItemSearch(
            url=TestItemSearch.SEARCH_URL,
            ids=ids,
        ))

        assert len(results) == 2
        assert all(item.id in ids for item in results)

    @pytest.mark.vcr
    def test_datetime_results(self):
        # Datetime range string
        datetime_ = '2019-01-01T00:00:01Z/2019-01-01T00:00:10Z'
        results = list(ItemSearch(
            url=TestItemSearch.SEARCH_URL,
            datetime=datetime_
        ))
        assert len(results) == 12

        min_datetime = datetime(2019, 1, 1, 0, 0, 1, tzinfo=tzutc())
        max_datetime = datetime(2019, 1, 1, 0, 0, 10, tzinfo=tzutc())
        results = ItemSearch(
            url=TestItemSearch.SEARCH_URL,
            datetime=(min_datetime, max_datetime)
        )
        assert all(min_datetime <= item.datetime <= (max_datetime + timedelta(seconds=1))for item in results)

    @pytest.mark.vcr
    def test_intersects_results(self):
        # GeoJSON-like dict
        intersects_dict = {
            'type': 'Polygon',
            'coordinates': [[
                [-73.21, 43.99],
                [-73.21, 44.05],
                [-73.12, 44.05],
                [-73.12, 43.99],
                [-73.21, 43.99]
            ]]
        }
        results = list(ItemSearch(
            url=TestItemSearch.SEARCH_URL,
            intersects=intersects_dict,
            collections='naip'
        ))
        assert len(results) == 30

        # Geo-interface object
        class MockGeoObject:
            __geo_interface__ = intersects_dict

        intersects_obj = MockGeoObject()
        results = ItemSearch(
            url=TestItemSearch.SEARCH_URL,
            intersects=intersects_obj,
            collections='naip'
        )
        assert all(isinstance(item, pystac.Item) for item in results)

    @pytest.mark.vcr
    def test_result_paging(self):
        search = ItemSearch(
            url=TestItemSearch.SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections='naip',
            limit=10,
            max_items=20,
        )

        # Check that the current page changes on the ItemSearch instance when a new page is requested
        pages = list(search.item_collections())

        assert pages[1] != pages[2]
        assert pages[1].features != pages[2].features
