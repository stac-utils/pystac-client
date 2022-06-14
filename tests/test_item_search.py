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
    "type": "Polygon",
    "coordinates": [
        [
            [-73.21, 43.99],
            [-73.21, 44.05],
            [-73.12, 44.05],
            [-73.12, 43.99],
            [-73.21, 43.99],
        ]
    ],
}

ITEM_EXAMPLE = {"collections": "io-lulc", "ids": "60U-2020"}


class TestItemPerformance:
    @pytest.fixture(scope="function")
    def single_href(self) -> None:
        item_href = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/{collections}/items/{ids}".format(
            collections=ITEM_EXAMPLE["collections"], ids=ITEM_EXAMPLE["ids"]
        )
        return item_href

    def test_requests(self, benchmark, single_href):
        response = benchmark(requests.get, single_href)
        assert response.status_code == 200

        assert response.json()["id"] == ITEM_EXAMPLE["ids"]

    def test_single_item(self, benchmark, single_href):
        item = benchmark(pystac.Item.from_file, single_href)

        assert item.id == ITEM_EXAMPLE["ids"]

    def test_single_item_search(self, benchmark, single_href):
        search = ItemSearch(url=SEARCH_URL, **ITEM_EXAMPLE)

        item_collection = benchmark(search.get_all_items)

        assert len(item_collection.items) == 1
        assert item_collection.items[0].id == ITEM_EXAMPLE["ids"]


class TestItemSearchParams:
    @pytest.fixture(scope="function")
    def sample_client(self) -> None:
        api_content = read_data_file("planetary-computer-root.json", parse_json=True)
        return Client.from_dict(api_content)

    def test_tuple_bbox(self) -> None:
        # Tuple input
        search = ItemSearch(url=SEARCH_URL, bbox=(-104.5, 44.0, -104.0, 45.0))
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_list_bbox(self) -> None:
        # List input
        search = ItemSearch(url=SEARCH_URL, bbox=[-104.5, 44.0, -104.0, 45.0])
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_string_bbox(self) -> None:
        # String Input
        search = ItemSearch(url=SEARCH_URL, bbox="-104.5,44.0,-104.0,45.0")
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_generator_bbox(self) -> None:
        # Generator Input
        def bboxer():
            yield from [-104.5, 44.0, -104.0, 45.0]

        search = ItemSearch(url=SEARCH_URL, bbox=bboxer())
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_single_string_datetime(self) -> None:
        # Single timestamp input
        search = ItemSearch(url=SEARCH_URL, datetime="2020-02-01T00:00:00Z")
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z"

    def test_range_string_datetime(self) -> None:
        # Timestamp range input
        search = ItemSearch(
            url=SEARCH_URL, datetime="2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )
        assert (
            search.get_parameters()["datetime"]
            == "2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )

    def test_list_of_strings_datetime(self) -> None:
        # Timestamp list input
        search = ItemSearch(
            url=SEARCH_URL, datetime=["2020-02-01T00:00:00Z", "2020-02-02T00:00:00Z"]
        )
        assert (
            search.get_parameters()["datetime"]
            == "2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )

    def test_open_range_string_datetime(self) -> None:
        # Open timestamp range input
        search = ItemSearch(url=SEARCH_URL, datetime="2020-02-01T00:00:00Z/..")
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z/.."

    def test_single_datetime_object(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())

        # Single datetime input
        search = ItemSearch(url=SEARCH_URL, datetime=start)
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z"

    def test_list_of_datetimes(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())

        # Datetime range input
        search = ItemSearch(url=SEARCH_URL, datetime=[start, end])
        assert (
            search.get_parameters()["datetime"]
            == "2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )

    def test_open_list_of_datetimes(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())

        # Open datetime range input
        search = ItemSearch(url=SEARCH_URL, datetime=(start, None))
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z/.."

    def test_localized_datetime_converted_to_utc(self) -> None:
        # Localized datetime input (should be converted to UTC)
        start_localized = datetime(2020, 2, 1, 0, 0, 0, tzinfo=gettz("US/Eastern"))
        search = ItemSearch(url=SEARCH_URL, datetime=start_localized)
        assert search.get_parameters()["datetime"] == "2020-02-01T05:00:00Z"

    def test_single_year(self) -> None:
        search = ItemSearch(url=SEARCH_URL, datetime="2020")
        assert (
            search.get_parameters()["datetime"]
            == "2020-01-01T00:00:00Z/2020-12-31T23:59:59Z"
        )

    def test_range_of_years(self) -> None:
        search = ItemSearch(url=SEARCH_URL, datetime="2019/2020")
        assert (
            search.get_parameters()["datetime"]
            == "2019-01-01T00:00:00Z/2020-12-31T23:59:59Z"
        )

    def test_single_month(self) -> None:
        search = ItemSearch(url=SEARCH_URL, datetime="2020-06")
        assert (
            search.get_parameters()["datetime"]
            == "2020-06-01T00:00:00Z/2020-06-30T23:59:59Z"
        )

    def test_range_of_months(self) -> None:
        search = ItemSearch(url=SEARCH_URL, datetime="2020-04/2020-06")
        assert (
            search.get_parameters()["datetime"]
            == "2020-04-01T00:00:00Z/2020-06-30T23:59:59Z"
        )

    def test_single_date(self) -> None:
        search = ItemSearch(url=SEARCH_URL, datetime="2020-06-10")
        assert (
            search.get_parameters()["datetime"]
            == "2020-06-10T00:00:00Z/2020-06-10T23:59:59Z"
        )

    def test_range_of_dates(self) -> None:
        search = ItemSearch(url=SEARCH_URL, datetime="2020-06-10/2020-06-20")
        assert (
            search.get_parameters()["datetime"]
            == "2020-06-10T00:00:00Z/2020-06-20T23:59:59Z"
        )

    def test_mixed_simple_date_strings(self) -> None:
        search = ItemSearch(url=SEARCH_URL, datetime="2019/2020-06-10")
        assert (
            search.get_parameters()["datetime"]
            == "2019-01-01T00:00:00Z/2020-06-10T23:59:59Z"
        )

    def test_time(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL, datetime="2019-01-01T00:00:00Z/2019-01-01T00:12:00"
        )
        assert (
            search.get_parameters()["datetime"]
            == "2019-01-01T00:00:00Z/2019-01-01T00:12:00Z"
        )

    def test_many_datetimes(self) -> None:
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

    def test_three_datetimes(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        middle = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 3, 0, 0, 0, tzinfo=tzutc())

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, datetime=[start, middle, end])

    def test_single_collection_string(self) -> None:
        # Single ID string
        search = ItemSearch(url=SEARCH_URL, collections="naip")
        assert search.get_parameters()["collections"] == ("naip",)

    def test_multiple_collection_string(self) -> None:
        # Comma-separated ID string
        search = ItemSearch(url=SEARCH_URL, collections="naip,landsat8_l1tp")
        assert search.get_parameters()["collections"] == ("naip", "landsat8_l1tp")

    def test_list_of_collection_strings(self) -> None:
        # List of ID strings
        search = ItemSearch(url=SEARCH_URL, collections=["naip", "landsat8_l1tp"])
        assert search.get_parameters()["collections"] == ("naip", "landsat8_l1tp")

    def test_generator_of_collection_strings(self) -> None:
        # Generator of ID strings
        def collectioner():
            yield from ["naip", "landsat8_l1tp"]

        search = ItemSearch(url=SEARCH_URL, collections=collectioner())
        assert search.get_parameters()["collections"] == ("naip", "landsat8_l1tp")

    def test_single_id_string(self) -> None:
        # Single ID
        search = ItemSearch(url=SEARCH_URL, ids="m_3510836_se_12_060_20180508_20190331")
        assert search.get_parameters()["ids"] == (
            "m_3510836_se_12_060_20180508_20190331",
        )

    def test_multiple_id_string(self) -> None:
        # Comma-separated ID string
        search = ItemSearch(
            url=SEARCH_URL,
            ids="m_3510836_se_12_060_20180508_20190331,m_3510840_se_12_060_20180504_20190331",
        )
        assert search.get_parameters()["ids"] == (
            "m_3510836_se_12_060_20180508_20190331",
            "m_3510840_se_12_060_20180504_20190331",
        )

    def test_list_of_id_strings(self) -> None:
        # List of IDs
        search = ItemSearch(
            url=SEARCH_URL,
            ids=[
                "m_3510836_se_12_060_20180508_20190331",
                "m_3510840_se_12_060_20180504_20190331",
            ],
        )
        assert search.get_parameters()["ids"] == (
            "m_3510836_se_12_060_20180508_20190331",
            "m_3510840_se_12_060_20180504_20190331",
        )

    def test_generator_of_id_string(self) -> None:
        # Generator of IDs
        def ids():
            yield from [
                "m_3510836_se_12_060_20180508_20190331",
                "m_3510840_se_12_060_20180504_20190331",
            ]

        search = ItemSearch(url=SEARCH_URL, ids=ids())
        assert search.get_parameters()["ids"] == (
            "m_3510836_se_12_060_20180508_20190331",
            "m_3510840_se_12_060_20180504_20190331",
        )

    def test_intersects_dict(self) -> None:
        # Dict input
        search = ItemSearch(url=SEARCH_URL, intersects=INTERSECTS_EXAMPLE)
        assert search.get_parameters()["intersects"] == INTERSECTS_EXAMPLE

    def test_intersects_json_string(self) -> None:
        # JSON string input
        search = ItemSearch(url=SEARCH_URL, intersects=json.dumps(INTERSECTS_EXAMPLE))
        assert search.get_parameters()["intersects"] == INTERSECTS_EXAMPLE

    def test_intersects_non_geo_interface_object(self) -> None:
        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, intersects=object())

    def test_filter_lang_default_for_dict(self) -> None:
        search = ItemSearch(url=SEARCH_URL, filter={})
        assert search.get_parameters()["filter-lang"] == "cql2-json"

    def test_filter_lang_default_for_str(self) -> None:
        search = ItemSearch(url=SEARCH_URL, filter="")
        assert search.get_parameters()["filter-lang"] == "cql2-text"

    def test_filter_lang_cql2_text(self) -> None:
        # Use specified filter_lang
        search = ItemSearch(url=SEARCH_URL, filter_lang="cql2-text", filter={})
        assert search.get_parameters()["filter-lang"] == "cql2-text"

    def test_filter_lang_cql2_json(self) -> None:
        # Use specified filter_lang
        search = ItemSearch(url=SEARCH_URL, filter_lang="cql2-json", filter="")
        assert search.get_parameters()["filter-lang"] == "cql2-json"

    def test_filter_lang_without_filter(self) -> None:
        # No filter provided
        search = ItemSearch(url=SEARCH_URL)
        assert "filter-lang" not in search.get_parameters()

    def test_sortby(self) -> None:
        search = ItemSearch(url=SEARCH_URL, sortby="properties.datetime")
        assert search.get_parameters()["sortby"] == [
            {"direction": "asc", "field": "properties.datetime"}
        ]

        search = ItemSearch(url=SEARCH_URL, sortby="+properties.datetime")
        assert search.get_parameters()["sortby"] == [
            {"direction": "asc", "field": "properties.datetime"}
        ]

        search = ItemSearch(url=SEARCH_URL, sortby="-properties.datetime")
        assert search.get_parameters()["sortby"] == [
            {"direction": "desc", "field": "properties.datetime"}
        ]

        search = ItemSearch(
            url=SEARCH_URL, sortby="-properties.datetime,+id,collection"
        )
        assert search.get_parameters()["sortby"] == [
            {"direction": "desc", "field": "properties.datetime"},
            {"direction": "asc", "field": "id"},
            {"direction": "asc", "field": "collection"},
        ]

        search = ItemSearch(
            url=SEARCH_URL,
            sortby=[
                {"direction": "desc", "field": "properties.datetime"},
                {"direction": "asc", "field": "id"},
                {"direction": "asc", "field": "collection"},
            ],
        )
        assert search.get_parameters()["sortby"] == [
            {"direction": "desc", "field": "properties.datetime"},
            {"direction": "asc", "field": "id"},
            {"direction": "asc", "field": "collection"},
        ]

        search = ItemSearch(
            url=SEARCH_URL, sortby=["-properties.datetime", "id", "collection"]
        )
        assert search.get_parameters()["sortby"] == [
            {"direction": "desc", "field": "properties.datetime"},
            {"direction": "asc", "field": "id"},
            {"direction": "asc", "field": "collection"},
        ]

        search = ItemSearch(
            url=SEARCH_URL,
            method="GET",
            sortby=["-properties.datetime", "id", "collection"],
        )
        assert (
            search.get_parameters()["sortby"] == "-properties.datetime,+id,+collection"
        )

        search = ItemSearch(
            url=SEARCH_URL, method="GET", sortby="-properties.datetime,id,collection"
        )
        assert (
            search.get_parameters()["sortby"] == "-properties.datetime,+id,+collection"
        )

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, sortby=1)

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, sortby=[1])

    def test_fields(self):

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, fields=1)

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, fields=[1])

        search = ItemSearch(url=SEARCH_URL, fields="id,collection,+foo,-bar")
        assert search.get_parameters()["fields"] == {
            "excludes": ["bar"],
            "includes": ["id", "collection", "foo"],
        }

        search = ItemSearch(url=SEARCH_URL, fields=["id", "collection", "+foo", "-bar"])
        assert search.get_parameters()["fields"] == {
            "excludes": ["bar"],
            "includes": ["id", "collection", "foo"],
        }

        search = ItemSearch(
            url=SEARCH_URL,
            fields={"excludes": ["bar"], "includes": ["id", "collection"]},
        )
        assert search.get_parameters()["fields"] == {
            "excludes": ["bar"],
            "includes": ["id", "collection"],
        }

        search = ItemSearch(
            url=SEARCH_URL, method="GET", fields="id,collection,+foo,-bar"
        )
        assert search.get_parameters()["fields"] == "+id,+collection,+foo,-bar"

        search = ItemSearch(
            url=SEARCH_URL, method="GET", fields=["id", "collection", "+foo", "-bar"]
        )
        assert search.get_parameters()["fields"] == "+id,+collection,+foo,-bar"

        search = ItemSearch(
            url=SEARCH_URL,
            method="GET",
            fields={"excludes": ["bar"], "includes": ["id", "collection"]},
        )
        assert search.get_parameters()["fields"] == "+id,+collection,-bar"

    def test_freetext(self):
        search = ItemSearch(url=SEARCH_URL, q="*")
        assert search._parameters['q'] == "*"


class TestItemSearch:
    @pytest.fixture(scope="function")
    def astraea_api(self) -> None:
        api_content = read_data_file("astraea_api.json", parse_json=True)
        return Client.from_dict(api_content)

    def test_method(self) -> None:
        # Default method should be POST...
        search = ItemSearch(url=SEARCH_URL)
        assert search.method == "POST"

        # "method" argument should take precedence over presence of "intersects"
        search = ItemSearch(url=SEARCH_URL, method="GET", intersects=INTERSECTS_EXAMPLE)
        assert search.method == "GET"

    def test_method_params(self) -> None:
        params_in = {
            "bbox": (-72, 41, -71, 42),
            "ids": (
                "idone",
                "idtwo",
            ),
            "collections": ("collectionone",),
            "intersects": INTERSECTS_EXAMPLE,
        }
        # For POST this is pass through
        search = ItemSearch(url=SEARCH_URL, **params_in)
        params = search.get_parameters()
        assert params == search.get_parameters()

        # For GET requests, parameters are in query string and must be serialized
        search = ItemSearch(url=SEARCH_URL, method="GET", **params_in)
        params = search.get_parameters()
        assert all(key in params for key in params_in)
        assert all(isinstance(params[key], str) for key in params_in)

    @pytest.mark.vcr
    def test_results(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            collections="naip",
            max_items=20,
            limit=10,
        )
        results = search.items()

        assert all(isinstance(item, pystac.Item) for item in results)

    @pytest.mark.vcr
    def test_ids_results(self) -> None:
        ids = [
            "S2B_MSIL2A_20210610T115639_N0212_R066_T33XXG_20210613T185024.SAFE",
            "fl_m_2608004_nw_17_060_20191215_20200113",
        ]
        search = ItemSearch(
            url=SEARCH_URL,
            ids=ids,
        )
        results = list(search.items())

        assert len(results) == 1
        assert all(item.id in ids for item in results)

    @pytest.mark.vcr
    def test_datetime_results(self) -> None:
        # Datetime range string
        datetime_ = "2019-01-01T00:00:01Z/2019-01-01T00:00:10Z"
        search = ItemSearch(url=SEARCH_URL, datetime=datetime_)
        results = list(search.items())
        assert len(results) == 33

        min_datetime = datetime(2019, 1, 1, 0, 0, 1, tzinfo=tzutc())
        max_datetime = datetime(2019, 1, 1, 0, 0, 10, tzinfo=tzutc())
        search = ItemSearch(url=SEARCH_URL, datetime=(min_datetime, max_datetime))
        results = search.items()
        assert all(
            min_datetime <= item.datetime <= (max_datetime + timedelta(seconds=1))
            for item in results
        )

    @pytest.mark.vcr
    def test_intersects_results(self) -> None:
        # GeoJSON-like dict
        intersects_dict = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-73.21, 43.99],
                    [-73.21, 44.05],
                    [-73.12, 44.05],
                    [-73.12, 43.99],
                    [-73.21, 43.99],
                ]
            ],
        }
        search = ItemSearch(
            url=SEARCH_URL, intersects=intersects_dict, collections="naip"
        )
        results = list(search.items())
        assert len(results) == 30

        # Geo-interface object
        class MockGeoObject:
            @property
            def __geo_interface__(self) -> None:
                return intersects_dict

        intersects_obj = MockGeoObject()
        search = ItemSearch(
            url=SEARCH_URL, intersects=intersects_obj, collections="naip"
        )
        results = search.items()
        assert all(isinstance(item, pystac.Item) for item in results)

    def test_freetext_results(self):
        search = ItemSearch(
            url=f"{STAC_URLS['CEDA']}/search",
            collections='cmip6',
            limit=10,
            max_items=20,
            q="aerchemm*"
        )
        results = search.get_items()
        item = next(results)

        assert all(isinstance(item, pystac.Item) for item in results)
        assert all(item.properties['activity_id'][0].lower().startswith("aerchemm") for item in results)

    @pytest.mark.vcr
    def test_result_paging(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections="naip",
            limit=10,
            max_items=20,
        )

        # Check that the current page changes on the ItemSearch instance when a new page is requested
        pages = list(search.item_collections())

        assert pages[1] != pages[2]
        assert pages[1].items != pages[2].items

    @pytest.mark.vcr
    def test_get_all_items(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections="naip",
            limit=10,
            max_items=20,
        )
        item_collection = search.get_all_items()
        assert len(item_collection.items) == 20

    @pytest.mark.vcr
    def test_items_as_dicts(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections="naip",
            limit=10,
            max_items=20,
        )
        assert len(list(search.items_as_dicts())) == 20


class TestItemSearchQuery:
    @pytest.mark.vcr
    def test_query_shortcut_syntax(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query=["gsd=10"],
            max_items=1,
        )
        items1 = list(search.items())

        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query={"gsd": {"eq": 10}},
            max_items=1,
        )
        items2 = list(search.items())

        assert len(items1) == 1
        assert len(items2) == 1
        assert items1[0].id == items2[0].id

    @pytest.mark.vcr
    def test_query_json_syntax(self) -> None:

        # with a list of json strs (format of CLI argument to ItemSearch)
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query=['{"eo:cloud_cover": { "gte": 0, "lte": 1 }}'],
            max_items=1,
        )
        item1 = list(search.items())[0]
        assert item1.properties["eo:cloud_cover"] <= 1

        # with a single dict
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query={"eo:cloud_cover": {"gte": 0, "lte": 1}},
            max_items=1,
        )
        item2 = list(search.items())[0]
        assert item2.properties["eo:cloud_cover"] <= 1

        assert item1.id == item2.id


def test_query_json_syntax() -> None:
    item_search = ItemSearch("")
    assert item_search._format_query(
        ['{"eo:cloud_cover": { "gte": 0, "lte": 1 }}']
    ) == {"eo:cloud_cover": {"gte": 0, "lte": 1}}
    assert item_search._format_query({"eo:cloud_cover": {"gte": 0, "lte": 1}}) == {
        "eo:cloud_cover": {"gte": 0, "lte": 1}
    }
    assert item_search._format_query(["eo:cloud_cover<=1"]) == {
        "eo:cloud_cover": {"lte": "1"}
    }
    assert item_search._format_query(["eo:cloud_cover<=1", "eo:cloud_cover>0"]) == {
        "eo:cloud_cover": {"lte": "1", "gt": "0"}
    }
