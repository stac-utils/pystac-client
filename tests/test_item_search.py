import json
from datetime import datetime, timedelta

import pystac
import pytest
import requests
from dateutil.tz import gettz, tzutc
from pystac_client import Client
from pystac_client.item_search import ItemSearch

from .helpers import STAC_URLS, read_data_file

SEARCH_URL = f"{STAC_URLS['PLANETARY-COMPUTER']}/search"
INTERSECTS_EXAMPLE = {
    'type':
    'Polygon',
    'coordinates': [[[-73.21, 43.99], [-73.21, 44.05], [-73.12, 44.05], [-73.12, 43.99],
                     [-73.21, 43.99]]]
}

ITEM_EXAMPLE = {"collections": "io-lulc", "ids": "60U-2020"}


@pytest.mark.skip(reason="Performance testing skipped in normal test run")
class TestItemPerformance:
    @pytest.fixture(scope='function')
    def single_href(self):
        item_href = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/{collections}/items/{ids}".format(
            collections=ITEM_EXAMPLE['collections'], ids=ITEM_EXAMPLE['ids'])
        return item_href

    def test_requests(self, benchmark, single_href):
        response = benchmark(requests.get, single_href)
        assert response.status_code == 200

        assert response.json()['id'] == ITEM_EXAMPLE["ids"]

    def test_single_item(self, benchmark, single_href):
        item = benchmark(pystac.Item.from_file, single_href)

        assert item.id == ITEM_EXAMPLE["ids"]

    def test_single_item_search(self, benchmark, single_href):
        search = ItemSearch(url=SEARCH_URL, **ITEM_EXAMPLE)

        item_collection = benchmark(search.get_all_items)

        assert len(item_collection.items) == 1
        assert item_collection.items[0].id == ITEM_EXAMPLE["ids"]


class TestItemSearchParams:
    @pytest.fixture(scope='function')
    def sample_client(self):
        api_content = read_data_file('planetary-computer-root.json', parse_json=True)
        return Client.from_dict(api_content)

    def test_tuple_bbox(self):
        # Tuple input
        search = ItemSearch(url=SEARCH_URL, bbox=(-104.5, 44.0, -104.0, 45.0))
        assert search._parameters['bbox'] == (-104.5, 44.0, -104.0, 45.0)

    def test_list_bbox(self):
        # List input
        search = ItemSearch(url=SEARCH_URL, bbox=[-104.5, 44.0, -104.0, 45.0])
        assert search._parameters['bbox'] == (-104.5, 44.0, -104.0, 45.0)

    def test_string_bbox(self):
        # String Input
        search = ItemSearch(url=SEARCH_URL, bbox='-104.5,44.0,-104.0,45.0')
        assert search._parameters['bbox'] == (-104.5, 44.0, -104.0, 45.0)

    def test_generator_bbox(self):
        # Generator Input
        def bboxer():
            yield from [-104.5, 44.0, -104.0, 45.0]

        search = ItemSearch(url=SEARCH_URL, bbox=bboxer())
        assert search._parameters['bbox'] == (-104.5, 44.0, -104.0, 45.0)

    def test_single_string_datetime(self):
        # Single timestamp input
        search = ItemSearch(url=SEARCH_URL, datetime='2020-02-01T00:00:00Z')
        assert search._parameters['datetime'] == '2020-02-01T00:00:00Z'

    def test_range_string_datetime(self):
        # Timestamp range input
        search = ItemSearch(url=SEARCH_URL, datetime='2020-02-01T00:00:00Z/2020-02-02T00:00:00Z')
        assert search._parameters['datetime'] == '2020-02-01T00:00:00Z/2020-02-02T00:00:00Z'

    def test_list_of_strings_datetime(self):
        # Timestamp list input
        search = ItemSearch(url=SEARCH_URL,
                            datetime=['2020-02-01T00:00:00Z', '2020-02-02T00:00:00Z'])
        assert search._parameters['datetime'] == '2020-02-01T00:00:00Z/2020-02-02T00:00:00Z'

    def test_open_range_string_datetime(self):
        # Open timestamp range input
        search = ItemSearch(url=SEARCH_URL, datetime='2020-02-01T00:00:00Z/..')
        assert search._parameters['datetime'] == '2020-02-01T00:00:00Z/..'

    def test_single_datetime_object(self):
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())

        # Single datetime input
        search = ItemSearch(url=SEARCH_URL, datetime=start)
        assert search._parameters['datetime'] == '2020-02-01T00:00:00Z'

    def test_list_of_datetimes(self):
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())

        # Datetime range input
        search = ItemSearch(url=SEARCH_URL, datetime=[start, end])
        assert search._parameters['datetime'] == '2020-02-01T00:00:00Z/2020-02-02T00:00:00Z'

    def test_open_list_of_datetimes(self):
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())

        # Open datetime range input
        search = ItemSearch(url=SEARCH_URL, datetime=(start, None))
        assert search._parameters['datetime'] == '2020-02-01T00:00:00Z/..'

    def test_localized_datetime_converted_to_utc(self):
        # Localized datetime input (should be converted to UTC)
        start_localized = datetime(2020, 2, 1, 0, 0, 0, tzinfo=gettz('US/Eastern'))
        search = ItemSearch(url=SEARCH_URL, datetime=start_localized)
        assert search._parameters['datetime'] == '2020-02-01T05:00:00Z'

    def test_single_year(self):
        search = ItemSearch(url=SEARCH_URL, datetime='2020')
        assert search._parameters['datetime'] == "2020-01-01T00:00:00Z/2020-12-31T23:59:59Z"

    def test_range_of_years(self):
        search = ItemSearch(url=SEARCH_URL, datetime='2019/2020')
        assert search._parameters['datetime'] == "2019-01-01T00:00:00Z/2020-12-31T23:59:59Z"

    def test_single_month(self):
        search = ItemSearch(url=SEARCH_URL, datetime='2020-06')
        assert search._parameters['datetime'] == "2020-06-01T00:00:00Z/2020-06-30T23:59:59Z"

    def test_range_of_months(self):
        search = ItemSearch(url=SEARCH_URL, datetime='2020-04/2020-06')
        assert search._parameters['datetime'] == "2020-04-01T00:00:00Z/2020-06-30T23:59:59Z"

    def test_single_date(self):
        search = ItemSearch(url=SEARCH_URL, datetime='2020-06-10')
        assert search._parameters['datetime'] == "2020-06-10T00:00:00Z/2020-06-10T23:59:59Z"

    def test_range_of_dates(self):
        search = ItemSearch(url=SEARCH_URL, datetime='2020-06-10/2020-06-20')
        assert search._parameters['datetime'] == "2020-06-10T00:00:00Z/2020-06-20T23:59:59Z"

    def test_mixed_simple_date_strings(self):
        search = ItemSearch(url=SEARCH_URL, datetime="2019/2020-06-10")
        assert search._parameters['datetime'] == "2019-01-01T00:00:00Z/2020-06-10T23:59:59Z"

    def test_time(self):
        search = ItemSearch(url=SEARCH_URL, datetime="2019-01-01T00:00:00Z/2019-01-01T00:12:00")
        assert search._parameters['datetime'] == "2019-01-01T00:00:00Z/2019-01-01T00:12:00Z"

    def test_many_datetimes(self):
        datetimes = [
            "1985-04-12T23:20:50.52Z",
            "1996-12-19T16:39:57-08:00",
            "1990-12-31T23:59:60Z",
            "1990-12-31T15:59:60-08:00",
            "1937-01-01T12:00:27.87+01:00",
            "1985-04-12T23:20:50.52Z",
            "1937-01-01T12:00:27.8710+01:00",
            "1937-01-01T12:00:27.8+01:00",
            "1937-01-01T12:00:27.8Z",
            "1985-04-12t23:20:50.5202020z",
            "2020-07-23T00:00:00Z",
            "2020-07-23T00:00:00.0Z",
            "2020-07-23T00:00:00.01Z",
            "2020-07-23T00:00:00.012Z",
            "2020-07-23T00:00:00.0123Z",
            "2020-07-23T00:00:00.01234Z",
            "2020-07-23T00:00:00.012345Z",
            "2020-07-23T00:00:00.000Z",
            "2020-07-23T00:00:00.000+03:00",
            "2020-07-23T00:00:00+03:00",
            "2020-07-23T00:00:00.000+03:00",
            "2020-07-23T00:00:00.000z",
        ]
        for date_time in datetimes:
            ItemSearch(url=SEARCH_URL, datetime=date_time)

    def test_three_datetimes(self):
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        middle = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 3, 0, 0, 0, tzinfo=tzutc())

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, datetime=[start, middle, end])

    def test_single_collection_string(self):
        # Single ID string
        search = ItemSearch(url=SEARCH_URL, collections='naip')
        assert search._parameters['collections'] == ('naip', )

    def test_multiple_collection_string(self):
        # Comma-separated ID string
        search = ItemSearch(url=SEARCH_URL, collections='naip,landsat8_l1tp')
        assert search._parameters['collections'] == ('naip', 'landsat8_l1tp')

    def test_list_of_collection_strings(self):
        # List of ID strings
        search = ItemSearch(url=SEARCH_URL, collections=['naip', 'landsat8_l1tp'])
        assert search._parameters['collections'] == ('naip', 'landsat8_l1tp')

    def test_generator_of_collection_strings(self):
        # Generator of ID strings
        def collectioner():
            yield from ['naip', 'landsat8_l1tp']

        search = ItemSearch(url=SEARCH_URL, collections=collectioner())
        assert search._parameters['collections'] == ('naip', 'landsat8_l1tp')

    def test_single_id_string(self):
        # Single ID
        search = ItemSearch(url=SEARCH_URL, ids='m_3510836_se_12_060_20180508_20190331')
        assert search._parameters['ids'] == ('m_3510836_se_12_060_20180508_20190331', )

    def test_multiple_id_string(self):
        # Comma-separated ID string
        search = ItemSearch(
            url=SEARCH_URL,
            ids='m_3510836_se_12_060_20180508_20190331,m_3510840_se_12_060_20180504_20190331')
        assert search._parameters['ids'] == ('m_3510836_se_12_060_20180508_20190331',
                                             'm_3510840_se_12_060_20180504_20190331')

    def test_list_of_id_strings(self):
        # List of IDs
        search = ItemSearch(
            url=SEARCH_URL,
            ids=['m_3510836_se_12_060_20180508_20190331', 'm_3510840_se_12_060_20180504_20190331'])
        assert search._parameters['ids'] == ('m_3510836_se_12_060_20180508_20190331',
                                             'm_3510840_se_12_060_20180504_20190331')

    def test_generator_of_id_string(self):
        # Generator of IDs
        def ids():
            yield from [
                'm_3510836_se_12_060_20180508_20190331', 'm_3510840_se_12_060_20180504_20190331'
            ]

        search = ItemSearch(url=SEARCH_URL, ids=ids())
        assert search._parameters['ids'] == ('m_3510836_se_12_060_20180508_20190331',
                                             'm_3510840_se_12_060_20180504_20190331')

    def test_intersects_dict(self):
        # Dict input
        search = ItemSearch(url=SEARCH_URL, intersects=INTERSECTS_EXAMPLE)
        assert search._parameters['intersects'] == INTERSECTS_EXAMPLE

    def test_intersects_json_string(self):
        # JSON string input
        search = ItemSearch(url=SEARCH_URL, intersects=json.dumps(INTERSECTS_EXAMPLE))
        assert search._parameters['intersects'] == INTERSECTS_EXAMPLE


class TestItemSearch:
    @pytest.fixture(scope='function')
    def astraea_api(self):
        api_content = read_data_file('astraea_api.json', parse_json=True)
        return Client.from_dict(api_content)

    def test_method(self):
        # Default method should be POST...
        search = ItemSearch(url=SEARCH_URL)
        assert search.method == 'POST'

        # "method" argument should take precedence over presence of "intersects"
        search = ItemSearch(url=SEARCH_URL, method='GET', intersects=INTERSECTS_EXAMPLE)
        assert search.method == 'GET'

    @pytest.mark.vcr
    def test_results(self):
        search = ItemSearch(
            url=SEARCH_URL,
            collections='naip',
            max_items=20,
            limit=10,
        )
        results = search.get_items()

        assert all(isinstance(item, pystac.Item) for item in results)

    @pytest.mark.vcr
    def test_ids_results(self):
        ids = [
            'S2B_MSIL2A_20210610T115639_N0212_R066_T33XXG_20210613T185024.SAFE',
            'fl_m_2608004_nw_17_060_20191215_20200113'
        ]
        search = ItemSearch(
            url=SEARCH_URL,
            ids=ids,
        )
        results = list(search.get_items())

        assert len(results) == 1
        assert all(item.id in ids for item in results)

    @pytest.mark.vcr
    def test_datetime_results(self):
        # Datetime range string
        datetime_ = '2019-01-01T00:00:01Z/2019-01-01T00:00:10Z'
        search = ItemSearch(url=SEARCH_URL, datetime=datetime_)
        results = list(search.get_items())
        assert len(results) == 33

        min_datetime = datetime(2019, 1, 1, 0, 0, 1, tzinfo=tzutc())
        max_datetime = datetime(2019, 1, 1, 0, 0, 10, tzinfo=tzutc())
        search = ItemSearch(url=SEARCH_URL, datetime=(min_datetime, max_datetime))
        results = search.get_items()
        assert all(min_datetime <= item.datetime <= (max_datetime + timedelta(seconds=1))
                   for item in results)

    @pytest.mark.vcr
    def test_intersects_results(self):
        # GeoJSON-like dict
        intersects_dict = {
            'type':
            'Polygon',
            'coordinates': [[[-73.21, 43.99], [-73.21, 44.05], [-73.12, 44.05], [-73.12, 43.99],
                             [-73.21, 43.99]]]
        }
        search = ItemSearch(url=SEARCH_URL, intersects=intersects_dict, collections='naip')
        results = list(search.get_items())
        assert len(results) == 30

        # Geo-interface object
        class MockGeoObject:
            __geo_interface__ = intersects_dict

        intersects_obj = MockGeoObject()
        search = ItemSearch(url=SEARCH_URL, intersects=intersects_obj, collections='naip')
        results = search.get_items()
        assert all(isinstance(item, pystac.Item) for item in results)

    @pytest.mark.vcr
    def test_result_paging(self):
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections='naip',
            limit=10,
            max_items=20,
        )

        # Check that the current page changes on the ItemSearch instance when a new page is requested
        pages = list(search.get_item_collections())

        assert pages[1] != pages[2]
        assert pages[1].items != pages[2].items

    @pytest.mark.vcr
    def test_get_all_items(self):
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections='naip',
            limit=10,
            max_items=20,
        )
        item_collection = search.get_all_items()
        assert len(item_collection.items) == 20


class TestItemSearchQuery:
    def test_query_shortcut_syntax(self):
        search = ItemSearch(url=SEARCH_URL,
                            bbox=(-73.21, 43.99, -73.12, 44.05),
                            query=["gsd=10"],
                            max_items=1)
        items1 = list(search.get_items())

        search = ItemSearch(url=SEARCH_URL,
                            bbox=(-73.21, 43.99, -73.12, 44.05),
                            query={"gsd": {
                                "eq": 10
                            }},
                            max_items=1)
        items2 = list(search.get_items())

        assert (len(items1) == 1)
        assert (len(items2) == 1)
        assert (items1[0].id == items2[0].id)
