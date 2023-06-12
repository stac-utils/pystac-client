import json
import operator
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator

import pystac
import pytest
import requests
from dateutil.tz import gettz, tzutc
from pytest_benchmark.fixture import BenchmarkFixture
from requests_mock import Mocker

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

ITEM_EXAMPLE: Dict[str, Any] = {"collections": "io-lulc", "ids": "60U-2020"}


class TestItemPerformance:
    @pytest.fixture(scope="function")
    def single_href(self) -> str:
        item_href = (
            "https://planetarycomputer.microsoft.com/api/stac/v1/collections/"
            f"{ITEM_EXAMPLE['collections']}/items/{ITEM_EXAMPLE['ids']}"
        )
        return item_href

    def test_requests(self, benchmark: BenchmarkFixture, single_href: str) -> None:
        response = benchmark(requests.get, single_href)
        assert response.status_code == 200

        assert response.json()["id"] == ITEM_EXAMPLE["ids"]

    def test_single_item(self, benchmark: BenchmarkFixture, single_href: str) -> None:
        item = benchmark(pystac.Item.from_file, single_href)

        assert item.id == ITEM_EXAMPLE["ids"]

    def test_single_item_search(
        self, benchmark: BenchmarkFixture, single_href: str
    ) -> None:
        search = ItemSearch(url=SEARCH_URL, **ITEM_EXAMPLE)

        item_collection = benchmark(search.item_collection())

        assert len(item_collection.items) == 1
        assert item_collection.items[0].id == ITEM_EXAMPLE["ids"]


class TestItemSearchParams:
    @pytest.fixture(scope="function")
    def sample_client(self) -> Client:
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
        def bboxer() -> Iterator[float]:
            yield from [-104.5, 44.0, -104.0, 45.0]

        search = ItemSearch(url=SEARCH_URL, bbox=bboxer())
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_url_with_parameters(self) -> None:
        # Single timestamp input
        search = ItemSearch(
            url=SEARCH_URL,
            datetime="2020-02-01T00:00:00Z",
            bbox=[-104.5, 44.0, -104.0, 45.0],
        )
        assert "bbox=-104.5%2C44.0%2C-104.0%2C45.0" in search.url_with_parameters()

        # Motivating example: https://github.com/stac-utils/pystac-client/issues/299
        search = ItemSearch(
            url="https://planetarycomputer.microsoft.com/api/stac/v1/search",
            collections=["cop-dem-glo-30"],
            bbox=[88.214, 27.927, 88.302, 28.034],
        )
        assert (
            search.url_with_parameters()
            == "https://planetarycomputer.microsoft.com/api/stac/v1/search?"
            "limit=100&bbox=88.214%2C27.927%2C88.302%2C28.034&collections=cop-dem-glo-30"
        )

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
            "/2023-01-01T00:00:00Z",
            "2023-01-01T00:00:00Z/",
        ]
        for date_time in datetimes:
            ItemSearch(url=SEARCH_URL, datetime=date_time)

    def test_three_datetimes(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        middle = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 3, 0, 0, 0, tzinfo=tzutc())

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, datetime=[start, middle, end])

    def test_double_open_ended_interval(self) -> None:
        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, datetime=[None, None])

    def test_datetime_list_of_one_none(self) -> None:
        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, datetime=[None])

    def test_poorly_formed_datetimes(self) -> None:
        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, datetime="2020-7/2020-8")

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
        def collectioner() -> Iterator[str]:
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
        def ids() -> Iterator[str]:
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
            ItemSearch(url=SEARCH_URL, intersects=object())  # type: ignore

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
            ItemSearch(url=SEARCH_URL, sortby=1)  # type: ignore

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, sortby=[1])  # type: ignore

    def test_fields(self) -> None:
        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, fields=1)  # type: ignore

        with pytest.raises(Exception):
            ItemSearch(url=SEARCH_URL, fields=[1])  # type: ignore

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


class TestItemSearch:
    @pytest.fixture(scope="function")
    def astraea_api(self) -> Client:
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
        params_in: Dict[str, Any] = {
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
        min_datetime = datetime(2019, 1, 1, 0, 0, 1, tzinfo=tzutc())
        max_datetime = datetime(2019, 1, 1, 0, 0, 10, tzinfo=tzutc())
        datetime_ = "2019-01-01T00:00:01Z/2019-01-01T00:00:10Z"
        search = ItemSearch(url=SEARCH_URL, datetime=datetime_, max_items=20)
        for item in search.items():
            assert item.datetime is not None
            assert (
                min_datetime <= item.datetime <= (max_datetime + timedelta(seconds=1))
            )
        search = ItemSearch(
            url=SEARCH_URL, datetime=(min_datetime, max_datetime), max_items=20
        )
        new_results = search.items()
        for item in new_results:
            assert item.datetime is not None
            assert (
                min_datetime <= item.datetime <= (max_datetime + timedelta(seconds=1))
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
        assert len(results) == 36

        # Geo-interface object
        class MockGeoObject:
            @property
            def __geo_interface__(self) -> Dict[str, Any]:
                return intersects_dict

        intersects_obj = MockGeoObject()
        search = ItemSearch(
            url=SEARCH_URL, intersects=intersects_obj, collections="naip"
        )
        new_results = search.items()
        assert all(isinstance(item, pystac.Item) for item in new_results)

    def test_get_with_query(self, requests_mock: Mocker) -> None:
        requests_mock.get(
            (
                f"{SEARCH_URL}?query=%7B%22eo%3Acloud_cover%22%3A%7B%22gte%22%3A0%2C%22lte%22%3A10%7D%7D"
            ),
            status_code=200,
            json={"features": [{"foo": "bar"}], "links": []},
        )
        items = list(
            ItemSearch(
                url=SEARCH_URL,
                method="GET",
                query={"eo:cloud_cover": {"gte": 0, "lte": 10}},
            ).items_as_dicts()
        )
        assert len(items) == 1

    @pytest.mark.vcr
    def test_result_paging(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections="naip",
            limit=10,
            max_items=20,
        )

        # Check that the current page changes on the ItemSearch instance when a new page
        # is requested
        pages = list(search.pages())

        assert pages[0] != pages[1]
        assert pages[0].items != pages[1].items

    @pytest.mark.vcr
    def test_result_paging_max_items(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            collections="naip",
            limit=10,
            max_items=25,
        )
        num_pages = 0
        items = list()
        for page in search.pages_as_dicts():
            num_pages += 1
            items.extend(page["features"])
        assert num_pages == 3
        assert len(items) == 25

    @pytest.mark.vcr
    def test_item_collection(self) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections="naip",
            limit=10,
            max_items=20,
        )
        item_collection = search.item_collection()
        assert isinstance(item_collection, pystac.ItemCollection)
        assert len(item_collection) == 20

    @pytest.mark.vcr
    @pytest.mark.parametrize(
        "method, alternative, is_sequence, is_pystac",
        [
            ("get_item_collections", "pages", True, True),
            ("item_collections", "pages", True, True),
            ("get_items", "items", True, True),
            ("get_all_items", "item_collection", False, True),
            ("get_all_items_as_dict", "item_collection_as_dict", False, False),
        ],
    )
    def test_deprecations(
        self, method: str, alternative: str, is_sequence: bool, is_pystac: bool
    ) -> None:
        search = ItemSearch(
            url=SEARCH_URL,
            bbox=(-73.21, 43.99, -73.12, 44.05),
            collections="naip",
            limit=10,
            max_items=20,
        )

        with pytest.warns(FutureWarning, match=method):
            result = operator.methodcaller(method)(search)

        expected = operator.methodcaller(alternative)(search)

        if is_sequence:
            result = list(result)
            expected = list(expected)
            if is_pystac:
                result = [x.to_dict() for x in result]
                expected = [x.to_dict() for x in expected]
        else:
            if is_pystac:
                result = result.to_dict()
                expected = expected.to_dict()

        assert result == expected

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
            collections="naip",
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query=["gsd=0.6"],
            max_items=1,
        )
        items1 = list(search.items())

        search = ItemSearch(
            url=SEARCH_URL,
            collections="naip",
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query={"gsd": {"eq": 0.6}},
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
            collections="naip",
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query=['{"gsd": { "gte": 0, "lte": 1 }}'],
            max_items=1,
        )
        item1 = list(search.items())[0]
        assert item1.properties["gsd"] <= 1

        # with a single dict
        search = ItemSearch(
            url=SEARCH_URL,
            collections="naip",
            bbox=(-73.21, 43.99, -73.12, 44.05),
            query={"gsd": {"gte": 0, "lte": 1}},
            max_items=1,
        )
        item2 = list(search.items())[0]
        assert item2.properties["gsd"] <= 1

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


def test_url_with_query_parameter() -> None:
    # https://github.com/stac-utils/pystac-client/issues/522
    search = ItemSearch(
        url="http://pystac-client.test", query={"eo:cloud_cover": {"lt": 42}}
    )
    url = urllib.parse.urlparse(search.url_with_parameters())
    query = urllib.parse.parse_qs(url.query)
    assert query["query"] == [r'{"eo:cloud_cover":{"lt":42}}']
