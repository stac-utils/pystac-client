import json
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest
from dateutil.tz import gettz, tzutc

from pystac_client import Client
from pystac_client.item_search import BaseSearch

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


class TestBaseSearchParams:
    @pytest.fixture(scope="function")
    def sample_client(self) -> Client:
        api_content = read_data_file("planetary-computer-root.json", parse_json=True)
        return Client.from_dict(api_content)

    def test_tuple_bbox(self) -> None:
        # Tuple input
        search = BaseSearch(url=SEARCH_URL, bbox=(-104.5, 44.0, -104.0, 45.0))
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_list_bbox(self) -> None:
        # List input
        search = BaseSearch(url=SEARCH_URL, bbox=[-104.5, 44.0, -104.0, 45.0])
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_string_bbox(self) -> None:
        # String Input
        search = BaseSearch(url=SEARCH_URL, bbox="-104.5,44.0,-104.0,45.0")
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_generator_bbox(self) -> None:
        # Generator Input
        def bboxer() -> Iterator[float]:
            yield from [-104.5, 44.0, -104.0, 45.0]

        search = BaseSearch(url=SEARCH_URL, bbox=bboxer())
        assert search.get_parameters()["bbox"] == (-104.5, 44.0, -104.0, 45.0)

    def test_url_with_parameters(self) -> None:
        # Single timestamp input
        search = BaseSearch(
            url=SEARCH_URL,
            datetime="2020-02-01T00:00:00Z",
            bbox=[-104.5, 44.0, -104.0, 45.0],
        )
        assert "bbox=-104.5%2C44.0%2C-104.0%2C45.0" in search.url_with_parameters()

        # Motivating example: https://github.com/stac-utils/pystac-client/issues/299
        search = BaseSearch(
            url="https://planetarycomputer.microsoft.com/api/stac/v1/search",
            collections=["cop-dem-glo-30"],
            bbox=[88.214, 27.927, 88.302, 28.034],
        )
        assert (
            search.url_with_parameters()
            == "https://planetarycomputer.microsoft.com/api/stac/v1/search?"
            "bbox=88.214%2C27.927%2C88.302%2C28.034&collections=cop-dem-glo-30"
        )

    def test_single_string_datetime(self) -> None:
        # Single timestamp input
        search = BaseSearch(url=SEARCH_URL, datetime="2020-02-01T00:00:00Z")
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z"

    def test_range_string_datetime(self) -> None:
        # Timestamp range input
        search = BaseSearch(
            url=SEARCH_URL, datetime="2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )
        assert (
            search.get_parameters()["datetime"]
            == "2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )

    def test_list_of_strings_datetime(self) -> None:
        # Timestamp list input
        search = BaseSearch(
            url=SEARCH_URL, datetime=["2020-02-01T00:00:00Z", "2020-02-02T00:00:00Z"]
        )
        assert (
            search.get_parameters()["datetime"]
            == "2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )

    def test_open_range_string_datetime(self) -> None:
        # Open timestamp range input
        search = BaseSearch(url=SEARCH_URL, datetime="2020-02-01T00:00:00Z/..")
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z/.."

    def test_single_datetime_object(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())

        # Single datetime input
        search = BaseSearch(url=SEARCH_URL, datetime=start)
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z"

    def test_list_of_datetimes(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())

        # Datetime range input
        search = BaseSearch(url=SEARCH_URL, datetime=[start, end])
        assert (
            search.get_parameters()["datetime"]
            == "2020-02-01T00:00:00Z/2020-02-02T00:00:00Z"
        )

    def test_open_list_of_datetimes(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())

        # Open datetime range input
        search = BaseSearch(url=SEARCH_URL, datetime=(start, None))
        assert search.get_parameters()["datetime"] == "2020-02-01T00:00:00Z/.."

    def test_localized_datetime_converted_to_utc(self) -> None:
        # Localized datetime input (should be converted to UTC)
        start_localized = datetime(2020, 2, 1, 0, 0, 0, tzinfo=gettz("US/Eastern"))
        search = BaseSearch(url=SEARCH_URL, datetime=start_localized)
        assert search.get_parameters()["datetime"] == "2020-02-01T05:00:00Z"

    def test_single_year(self) -> None:
        search = BaseSearch(url=SEARCH_URL, datetime="2020")
        assert (
            search.get_parameters()["datetime"]
            == "2020-01-01T00:00:00Z/2020-12-31T23:59:59Z"
        )

    def test_range_of_years(self) -> None:
        search = BaseSearch(url=SEARCH_URL, datetime="2019/2020")
        assert (
            search.get_parameters()["datetime"]
            == "2019-01-01T00:00:00Z/2020-12-31T23:59:59Z"
        )

    def test_single_month(self) -> None:
        search = BaseSearch(url=SEARCH_URL, datetime="2020-06")
        assert (
            search.get_parameters()["datetime"]
            == "2020-06-01T00:00:00Z/2020-06-30T23:59:59Z"
        )

    def test_range_of_months(self) -> None:
        search = BaseSearch(url=SEARCH_URL, datetime="2020-04/2020-06")
        assert (
            search.get_parameters()["datetime"]
            == "2020-04-01T00:00:00Z/2020-06-30T23:59:59Z"
        )

    def test_single_date(self) -> None:
        search = BaseSearch(url=SEARCH_URL, datetime="2020-06-10")
        assert (
            search.get_parameters()["datetime"]
            == "2020-06-10T00:00:00Z/2020-06-10T23:59:59Z"
        )

    def test_range_of_dates(self) -> None:
        search = BaseSearch(url=SEARCH_URL, datetime="2020-06-10/2020-06-20")
        assert (
            search.get_parameters()["datetime"]
            == "2020-06-10T00:00:00Z/2020-06-20T23:59:59Z"
        )

    def test_mixed_simple_date_strings(self) -> None:
        search = BaseSearch(url=SEARCH_URL, datetime="2019/2020-06-10")
        assert (
            search.get_parameters()["datetime"]
            == "2019-01-01T00:00:00Z/2020-06-10T23:59:59Z"
        )

    def test_time(self) -> None:
        search = BaseSearch(
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
            BaseSearch(url=SEARCH_URL, datetime=date_time)

    def test_three_datetimes(self) -> None:
        start = datetime(2020, 2, 1, 0, 0, 0, tzinfo=tzutc())
        middle = datetime(2020, 2, 2, 0, 0, 0, tzinfo=tzutc())
        end = datetime(2020, 2, 3, 0, 0, 0, tzinfo=tzutc())

        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, datetime=[start, middle, end])

    def test_double_open_ended_interval(self) -> None:
        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, datetime=[None, None])

    def test_datetime_list_of_one_none(self) -> None:
        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, datetime=[None])

    def test_poorly_formed_datetimes(self) -> None:
        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, datetime="2020-7/2020-8")

    def test_single_collection_string(self) -> None:
        # Single ID string
        search = BaseSearch(url=SEARCH_URL, collections="naip")
        assert search.get_parameters()["collections"] == ("naip",)

    def test_multiple_collection_string(self) -> None:
        # Comma-separated ID string
        search = BaseSearch(url=SEARCH_URL, collections="naip,landsat8_l1tp")
        assert search.get_parameters()["collections"] == ("naip", "landsat8_l1tp")

    def test_list_of_collection_strings(self) -> None:
        # List of ID strings
        search = BaseSearch(url=SEARCH_URL, collections=["naip", "landsat8_l1tp"])
        assert search.get_parameters()["collections"] == ("naip", "landsat8_l1tp")

    def test_generator_of_collection_strings(self) -> None:
        # Generator of ID strings
        def collectioner() -> Iterator[str]:
            yield from ["naip", "landsat8_l1tp"]

        search = BaseSearch(url=SEARCH_URL, collections=collectioner())
        assert search.get_parameters()["collections"] == ("naip", "landsat8_l1tp")

    def test_single_id_string(self) -> None:
        # Single ID
        search = BaseSearch(url=SEARCH_URL, ids="m_3510836_se_12_060_20180508_20190331")
        assert search.get_parameters()["ids"] == (
            "m_3510836_se_12_060_20180508_20190331",
        )

    def test_multiple_id_string(self) -> None:
        # Comma-separated ID string
        search = BaseSearch(
            url=SEARCH_URL,
            ids="m_3510836_se_12_060_20180508_20190331,m_3510840_se_12_060_20180504_20190331",
        )
        assert search.get_parameters()["ids"] == (
            "m_3510836_se_12_060_20180508_20190331",
            "m_3510840_se_12_060_20180504_20190331",
        )

    def test_list_of_id_strings(self) -> None:
        # List of IDs
        search = BaseSearch(
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

        search = BaseSearch(url=SEARCH_URL, ids=ids())
        assert search.get_parameters()["ids"] == (
            "m_3510836_se_12_060_20180508_20190331",
            "m_3510840_se_12_060_20180504_20190331",
        )

    def test_intersects_dict(self) -> None:
        # Dict input
        search = BaseSearch(url=SEARCH_URL, intersects=INTERSECTS_EXAMPLE)
        assert search.get_parameters()["intersects"] == INTERSECTS_EXAMPLE

    def test_intersects_json_string(self) -> None:
        # JSON string input
        search = BaseSearch(url=SEARCH_URL, intersects=json.dumps(INTERSECTS_EXAMPLE))
        assert search.get_parameters()["intersects"] == INTERSECTS_EXAMPLE

    def test_intersects_non_geo_interface_object(self) -> None:
        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, intersects=object())  # type: ignore

    def test_filter_lang_default_for_dict(self) -> None:
        search = BaseSearch(url=SEARCH_URL, filter={})
        assert search.get_parameters()["filter-lang"] == "cql2-json"

    def test_filter_lang_default_for_str(self) -> None:
        search = BaseSearch(url=SEARCH_URL, filter="")
        assert search.get_parameters()["filter-lang"] == "cql2-text"

    def test_filter_lang_cql2_text(self) -> None:
        # Use specified filter_lang
        search = BaseSearch(url=SEARCH_URL, filter_lang="cql2-text", filter={})
        assert search.get_parameters()["filter-lang"] == "cql2-text"

    def test_filter_lang_cql2_json(self) -> None:
        # Use specified filter_lang
        search = BaseSearch(url=SEARCH_URL, filter_lang="cql2-json", filter="")
        assert search.get_parameters()["filter-lang"] == "cql2-json"

    def test_filter_lang_without_filter(self) -> None:
        # No filter provided
        search = BaseSearch(url=SEARCH_URL)
        assert "filter-lang" not in search.get_parameters()

    def test_sortby(self) -> None:
        search = BaseSearch(url=SEARCH_URL, sortby="properties.datetime")
        assert search.get_parameters()["sortby"] == [
            {"direction": "asc", "field": "properties.datetime"}
        ]

        search = BaseSearch(url=SEARCH_URL, sortby="+properties.datetime")
        assert search.get_parameters()["sortby"] == [
            {"direction": "asc", "field": "properties.datetime"}
        ]

        search = BaseSearch(url=SEARCH_URL, sortby="-properties.datetime")
        assert search.get_parameters()["sortby"] == [
            {"direction": "desc", "field": "properties.datetime"}
        ]

        search = BaseSearch(
            url=SEARCH_URL, sortby="-properties.datetime,+id,collection"
        )
        assert search.get_parameters()["sortby"] == [
            {"direction": "desc", "field": "properties.datetime"},
            {"direction": "asc", "field": "id"},
            {"direction": "asc", "field": "collection"},
        ]

        search = BaseSearch(
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

        search = BaseSearch(
            url=SEARCH_URL, sortby=["-properties.datetime", "id", "collection"]
        )
        assert search.get_parameters()["sortby"] == [
            {"direction": "desc", "field": "properties.datetime"},
            {"direction": "asc", "field": "id"},
            {"direction": "asc", "field": "collection"},
        ]

        search = BaseSearch(
            url=SEARCH_URL,
            method="GET",
            sortby=["-properties.datetime", "id", "collection"],
        )
        assert (
            search.get_parameters()["sortby"] == "-properties.datetime,+id,+collection"
        )

        search = BaseSearch(
            url=SEARCH_URL, method="GET", sortby="-properties.datetime,id,collection"
        )
        assert (
            search.get_parameters()["sortby"] == "-properties.datetime,+id,+collection"
        )

        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, sortby=1)  # type: ignore

        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, sortby=[1])  # type: ignore

    def test_fields(self) -> None:
        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, fields=1)  # type: ignore

        with pytest.raises(Exception):
            BaseSearch(url=SEARCH_URL, fields=[1])  # type: ignore

        search = BaseSearch(url=SEARCH_URL, fields="id,collection,+foo,-bar")
        assert search.get_parameters()["fields"] == {
            "exclude": ["bar"],
            "include": ["id", "collection", "foo"],
        }

        search = BaseSearch(url=SEARCH_URL, fields=["id", "collection", "+foo", "-bar"])
        assert search.get_parameters()["fields"] == {
            "exclude": ["bar"],
            "include": ["id", "collection", "foo"],
        }

        search = BaseSearch(
            url=SEARCH_URL,
            fields={"exclude": ["bar"], "include": ["id", "collection"]},
        )
        assert search.get_parameters()["fields"] == {
            "exclude": ["bar"],
            "include": ["id", "collection"],
        }

        search = BaseSearch(
            url=SEARCH_URL, method="GET", fields="id,collection,+foo,-bar"
        )
        assert search.get_parameters()["fields"] == "+id,+collection,+foo,-bar"

        search = BaseSearch(
            url=SEARCH_URL, method="GET", fields=["id", "collection", "+foo", "-bar"]
        )
        assert search.get_parameters()["fields"] == "+id,+collection,+foo,-bar"

        search = BaseSearch(
            url=SEARCH_URL,
            method="GET",
            fields={"exclude": ["bar"], "include": ["id", "collection"]},
        )
        assert search.get_parameters()["fields"] == "+id,+collection,-bar"
