import json
from datetime import datetime
from math import ceil
from typing import Any

import pystac
import pytest
import requests
from dateutil.tz import tzutc
from pytest_benchmark.fixture import BenchmarkFixture

from pystac_client.client import Client
from pystac_client.collection_search import (
    CollectionSearch,
    bboxes_overlap,
    collection_matches,
    temporal_intervals_overlap,
)
from pystac_client.warnings import PystacClientWarning

from .helpers import STAC_URLS, read_data_file

COLLECTION_SEARCH_URL = f"{STAC_URLS['SPACEBEL']}/collections"

COLLECTION_EXAMPLE: dict[str, Any] = {
    "id": "F-TCC",
    "q": '"cloudless mosaics"',
    "datetime": "2021-09-15T00:00:00Z",
}


class TestCollectionPerformance:
    @pytest.fixture(scope="function")
    def single_href(self) -> str:
        collection_href = COLLECTION_SEARCH_URL + f"/{COLLECTION_EXAMPLE['id']}"
        return collection_href

    def test_requests(self, benchmark: BenchmarkFixture, single_href: str) -> None:
        response = benchmark(requests.get, single_href)
        assert response.status_code == 200

        assert response.json()["id"] == COLLECTION_EXAMPLE["id"]

    def test_single_collection(
        self, benchmark: BenchmarkFixture, single_href: str
    ) -> None:
        collection = benchmark(pystac.Collection.from_file, single_href)

        assert collection.id == COLLECTION_EXAMPLE["id"]

    def test_single_collection_search(
        self, benchmark: BenchmarkFixture, single_href: str
    ) -> None:
        search = CollectionSearch(url=COLLECTION_SEARCH_URL, **COLLECTION_EXAMPLE)

        collection_list = benchmark(search.collection_list())

        assert len(collection_list) == 1
        assert collection_list[0].id == COLLECTION_EXAMPLE["id"]


class TestCollectionSearch:
    @pytest.fixture(scope="function")
    def fedeo_api(self) -> Client:
        api_content = read_data_file("fedeo_clearinghouse.json", parse_json=True)
        return Client.from_dict(api_content)

    def test_method(self) -> None:
        # Default method should be POST...
        search = CollectionSearch(url=COLLECTION_SEARCH_URL)
        assert search.method == "GET"

    def test_method_params(self) -> None:
        params_in: dict[str, Any] = {
            "bbox": (-72, 41, -71, 42),
            "datetime": "2021-01-01T00:00:00Z/2021-12-31T23:59:59Z",
            "q": "vegetation AND biomass",
        }
        # For POST this is pass through
        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            **params_in,
        )
        params = search.get_parameters()
        assert params == search.get_parameters()

        # For GET requests, parameters are in query string and must be serialized
        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            **params_in,
        )
        params = search.get_parameters()
        assert search.method == "GET"
        assert all(key in params for key in params_in)
        assert all(isinstance(params[key], str) for key in params_in)

    @pytest.mark.vcr
    def test_q_results(self) -> None:
        search_string = "monthly cloudless mosaics"
        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            q=f'"{search_string}"',
            max_collections=20,
            limit=10,
        )
        results = search.collection_list()

        assert all(isinstance(collection, pystac.Collection) for collection in results)
        assert all(search_string in collection.description for collection in results)

        assert search.matched() == 1

    @pytest.mark.vcr
    def test_datetime_results(self) -> None:
        min_datetime = datetime(2024, 1, 1, 0, 0, 1, tzinfo=tzutc())
        max_datetime = datetime(2024, 1, 1, 0, 0, 10, tzinfo=tzutc())
        datetime_ = "/".join(
            ts.isoformat().replace("+00:00", "Z") for ts in [min_datetime, max_datetime]
        )

        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            datetime=datetime_,
            max_collections=20,
        )

        for collection in search.collections():
            for temporal_intervals in collection.extent.temporal.intervals:
                assert temporal_intervals_overlap(
                    (temporal_intervals[0], temporal_intervals[1]),
                    (min_datetime, max_datetime),
                )

        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            datetime=(min_datetime, max_datetime),
            max_collections=20,
        )

        new_results = search.collections()
        for collection in new_results:
            for temporal_intervals in collection.extent.temporal.intervals:
                assert temporal_intervals_overlap(
                    (temporal_intervals[0], temporal_intervals[1]),
                    (min_datetime, max_datetime),
                )

    @pytest.mark.vcr
    def test_bbox_results(self) -> None:
        bbox = (-159.893, 21.843, -159.176, 22.266)
        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            bbox=bbox,
            limit=10,
            max_collections=10,
        )

        for collection in search.collections():
            for _bbox in collection.extent.spatial.bboxes:
                assert bboxes_overlap(bbox, tuple(float(coord) for coord in _bbox))

    @pytest.mark.vcr
    def test_result_paging(self) -> None:
        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            q="sentinel",
            limit=10,
            max_collections=20,
        )

        # Check that the current page changes on the ItemSearch instance when a new page
        # is requested
        pages = list(search.pages())

        assert pages[0] != pages[1]

    @pytest.mark.vcr
    def test_matched(self) -> None:
        q = "sentinel"
        search = CollectionSearch(
            url=f"{STAC_URLS['EARTH-SEARCH']}/collections",
            collection_search_extension_enabled=False,
            collection_search_free_text_enabled=False,
            q=q,
            limit=4,
        )

        assert search.matched() == 5

    @pytest.mark.vcr
    def test_enabled_but_client_side_q(self) -> None:
        q = "sentinel"
        limit = 5
        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=False,
            limit=limit,
            max_collections=limit,
            q=q,
        )

        collection_list = search.collection_list()
        assert len(collection_list) <= limit
        collection_list_dict = search.collection_list_as_dict()
        assert len(collection_list_dict["collections"]) == len(collection_list)

        for collection in search.collections():
            text_fields = []
            if collection.description:
                text_fields.append(collection.description)
            if collection.title:
                text_fields.append(collection.title)
            if collection.keywords:
                text_fields.extend(collection.keywords)

            assert any(q in text_field.lower() for text_field in text_fields), (
                f"{collection.id} failed check"
            )

    @pytest.mark.vcr
    def test_client_side_q(self) -> None:
        q = "sentinel"
        limit = 10
        search = CollectionSearch(
            url=f"{STAC_URLS['EARTH-SEARCH']}/collections",
            collection_search_extension_enabled=False,
            collection_search_free_text_enabled=False,
            limit=limit,
            max_collections=limit,
            q=q,
        )

        collection_list = search.collection_list()
        assert len(collection_list) <= limit

        for collection in search.collections():
            text_fields = []
            if collection.description:
                text_fields.append(collection.description)
            if collection.title:
                text_fields.append(collection.title)
            if collection.keywords:
                text_fields.extend(collection.keywords)

            assert any(q in text_field.lower() for text_field in text_fields), (
                f"{collection.id} failed check"
            )

    @pytest.mark.vcr
    def test_client_side_bbox(self) -> None:
        bbox = (60, 0, 70, 10)
        limit = 10
        search = CollectionSearch(
            url=f"{STAC_URLS['EARTH-SEARCH']}/collections",
            collection_search_extension_enabled=False,
            collection_search_free_text_enabled=False,
            limit=limit,
            max_collections=limit,
            bbox=bbox,
        )

        collection_list = search.collection_list()
        assert len(collection_list) <= limit

        for collection in search.collections():
            assert any(
                bboxes_overlap(bbox, tuple(float(coord) for coord in collection_bbox))
                for collection_bbox in collection.extent.spatial.bboxes
            ), f"{collection.id} failed check"

    @pytest.mark.vcr
    def test_client_side_datetime(self) -> None:
        _datetime_interval = ("2024-09-15T00:00:00+00:00", "2024-09-16T00:00:00+00:00")
        limit = 10
        search = CollectionSearch(
            url=f"{STAC_URLS['EARTH-SEARCH']}/collections",
            collection_search_extension_enabled=False,
            collection_search_free_text_enabled=False,
            limit=limit,
            max_collections=limit,
            datetime="/".join(_datetime_interval),
        )

        collection_list = search.collection_list()
        assert len(collection_list) <= limit

        temporal_interval = (
            datetime.fromisoformat(_datetime_interval[0]),
            datetime.fromisoformat(_datetime_interval[1]),
        )
        for collection in search.collections():
            assert any(
                temporal_intervals_overlap(
                    temporal_interval,
                    (collection_temporal_interval[0], collection_temporal_interval[1]),
                )
                for collection_temporal_interval in collection.extent.temporal.intervals
            ), f"{collection.id} failed check"

    def test_client_side_extra_args(self) -> None:
        with pytest.raises(ValueError):
            CollectionSearch(
                url=f"{STAC_URLS['EARTH-SEARCH']}/collections",
                collection_search_extension_enabled=False,
                collection_search_free_text_enabled=False,
                filter="title LIKE '%nope%'",
            )

    @pytest.mark.vcr
    def test_result_paging_max_collections(self) -> None:
        max_collections = 15
        limit = 10
        search = CollectionSearch(
            url=COLLECTION_SEARCH_URL,
            collection_search_extension_enabled=True,
            collection_search_free_text_enabled=True,
            bbox=(-92.379, 46.662, -91.788, 46.919),
            limit=limit,
            max_collections=max_collections,
        )
        num_pages = 0
        collections = list()
        for page in search.pages_as_dicts():
            num_pages += 1
            collections.extend(page["collections"])
        assert num_pages == ceil(max_collections / limit)
        assert len(collections) == max_collections


def test_bboxes_overlap() -> None:
    assert bboxes_overlap(
        (0, 0, 2, 2),
        (1, 1, 3, 3),
    )

    assert not bboxes_overlap(
        (0, 0, 2, 2),
        (3, 3, 4, 4),
    )


def test_temporal_intervals_overlap() -> None:
    assert temporal_intervals_overlap(
        (datetime(2024, 9, 1, tzinfo=tzutc()), datetime(2024, 9, 2, tzinfo=tzutc())),
        (
            datetime(2024, 9, 1, 12, tzinfo=tzutc()),
            datetime(2024, 9, 2, 12, tzinfo=tzutc()),
        ),
    )
    assert temporal_intervals_overlap(
        (datetime(2024, 9, 1, tzinfo=tzutc()), None),
        (
            datetime(2024, 9, 1, 12, tzinfo=tzutc()),
            datetime(2024, 9, 2, 12, tzinfo=tzutc()),
        ),
    )
    assert temporal_intervals_overlap(
        (None, None),
        (
            datetime(2024, 9, 1, 12, tzinfo=tzutc()),
            datetime(2024, 9, 2, 12, tzinfo=tzutc()),
        ),
    )
    assert not temporal_intervals_overlap(
        (datetime(2023, 9, 1, tzinfo=tzutc()), datetime(2023, 9, 2, tzinfo=tzutc())),
        (
            datetime(2024, 9, 1, 12, tzinfo=tzutc()),
            datetime(2024, 9, 2, 12, tzinfo=tzutc()),
        ),
    )
    assert not temporal_intervals_overlap(
        (datetime(2023, 9, 1, tzinfo=tzutc()), datetime(2023, 9, 2, tzinfo=tzutc())),
        (
            datetime(2024, 9, 1, 12, tzinfo=tzutc()),
            None,
        ),
    )


def test_invalid_collection() -> None:
    # https://github.com/stac-utils/pystac-client/issues/786
    data = json.loads(read_data_file("invalid-collection.json"))
    with pytest.warns(PystacClientWarning):
        collection_matches(data)
