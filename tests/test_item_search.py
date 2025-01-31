import operator
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

import pystac
import pytest
import requests
from dateutil.tz import tzutc
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

ITEM_EXAMPLE: dict[str, Any] = {"collections": "io-lulc", "ids": "60U-2020"}


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
        params_in: dict[str, Any] = {
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
            def __geo_interface__(self) -> dict[str, Any]:
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


@pytest.mark.vcr
def test_multiple_collections() -> None:
    search = ItemSearch(
        url="https://earth-search.aws.element84.com/v1/search",
        collections=["sentinel-2-l2a", "landsat-c2-l2"],
        intersects={"type": "Point", "coordinates": [-105.1019, 40.1672]},
        datetime="2023-10-08",
    )
    collections = {item.collection_id for item in search.items()}
    assert collections == {"sentinel-2-l2a", "landsat-c2-l2"}


def test_naive_datetime() -> None:
    search = ItemSearch(
        url="https://earth-search.aws.element84.com/v1/search",
        datetime=datetime(2024, 5, 14, 4, 25, 42, tzinfo=None),
        method="POST",
    )
    assert search.get_parameters()["datetime"] == "2024-05-14T04:25:42Z"


@pytest.mark.vcr
def test_fields() -> None:
    search = ItemSearch(
        url="https://earth-search.aws.element84.com/v1/search",
        collections=["sentinel-2-c1-l2a"],
        intersects={"type": "Point", "coordinates": [-105.1019, 40.1672]},
        max_items=1,
        fields=["-geometry", "-assets", "-links"],
    )
    item = next(search.items_as_dicts())
    assert "geometry" not in item
    assert "assets" not in item
    assert "links" not in item


def test_feature() -> None:
    search = ItemSearch(
        url="https://earth-search.aws.element84.com/v1/search",
        intersects={
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-105.1019, 40.1672]},
        },
    )
    assert search.get_parameters()["intersects"] == {
        "type": "Point",
        "coordinates": [-105.1019, 40.1672],
    }
