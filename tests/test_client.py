import json
import os.path
import warnings
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pystac
import pytest
from dateutil.tz import tzutc
from pystac import MediaType
from requests_mock import Mocker

from pystac_client import Client, CollectionClient
from pystac_client._utils import Modifiable
from pystac_client.conformance import ConformanceClasses
from pystac_client.errors import ClientTypeError, IgnoredResultWarning

from .helpers import STAC_URLS, TEST_DATA, read_data_file


class TestAPI:
    @pytest.mark.vcr  # type: ignore[misc]
    def test_instance(self) -> None:
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])

        # An API instance is also a Catalog instance
        assert isinstance(api, pystac.Catalog)

        assert str(api) == "<Client id=microsoft-pc>"

    @pytest.mark.vcr  # type: ignore[misc]
    def test_links(self) -> None:
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])

        # Should be able to get collections via links as with a typical PySTAC Catalog
        collection_links = api.get_links("child")
        assert len(collection_links) > 0

        collections = list(api.get_collections())
        assert len(collection_links) == len(collections)

        first_child_link = api.get_single_link("child")
        assert first_child_link is not None
        first_collection = first_child_link.resolve_stac_object(root=api).target
        assert isinstance(first_collection, pystac.Collection)

    def test_spec_conformance(self) -> None:
        """Testing conformance against a ConformanceClass should allow APIs using legacy
        URIs to pass."""
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        assert client._stac_io is not None

        # Set conformsTo URIs to conform with STAC API - Core using official URI
        client._stac_io._conformance = ["https://api.stacspec.org/v1.0.0-beta.1/core"]

        assert client._stac_io.conforms_to(ConformanceClasses.CORE)

    @pytest.mark.vcr  # type: ignore[misc]
    def test_no_conformance(self) -> None:
        """Should raise a NotImplementedError if no conformance info can be found.
        Luckily, the test API doesn't publish a "conformance" link so we can just
        remove the "conformsTo" attribute to test this."""
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        assert client._stac_io is not None
        client._stac_io._conformance = []
        assert client._stac_io is not None

        with pytest.raises(NotImplementedError):
            client._stac_io.assert_conforms_to(ConformanceClasses.CORE)

        with pytest.raises(NotImplementedError):
            client._stac_io.assert_conforms_to(ConformanceClasses.ITEM_SEARCH)

    @pytest.mark.vcr  # type: ignore[misc]
    def test_no_stac_core_conformance(self) -> None:
        """Should raise a NotImplementedError if the API does not conform to the
        STAC API - Core spec."""
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        assert client._stac_io is not None
        assert client._stac_io._conformance is not None
        client._stac_io._conformance = client._stac_io._conformance[1:]

        with pytest.raises(NotImplementedError):
            client._stac_io.assert_conforms_to(ConformanceClasses.CORE)

        assert client._stac_io.conforms_to(ConformanceClasses.ITEM_SEARCH)

    @pytest.mark.vcr  # type: ignore[misc]
    def test_from_file(self) -> None:
        api = Client.from_file(STAC_URLS["PLANETARY-COMPUTER"])

        assert api.title == "Microsoft Planetary Computer STAC API"

    def test_invalid_url(self) -> None:
        with pytest.raises(TypeError):
            Client.open()  # type: ignore[call-arg]

    def test_get_collections_with_conformance(self, requests_mock: Mocker) -> None:
        """Checks that the "data" endpoint is used if the API published the
        STAC API Collections conformance class."""
        pc_root_text = read_data_file("planetary-computer-root.json")
        pc_collection_dict = read_data_file(
            "planetary-computer-aster-l1t-collection.json", parse_json=True
        )

        # Mock the root catalog
        requests_mock.get(
            STAC_URLS["PLANETARY-COMPUTER"], status_code=200, text=pc_root_text
        )
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        assert api._stac_io is not None

        assert api._stac_io.conforms_to(ConformanceClasses.COLLECTIONS)

        # Get & mock the collections (rel type "data") link
        collections_link = api.get_single_link("data")
        assert collections_link is not None
        requests_mock.get(
            collections_link.href,
            status_code=200,
            json={"collections": [pc_collection_dict], "links": []},
        )
        _ = next(api.get_collections())

        history = requests_mock.request_history
        assert len(history) == 2
        assert history[1].url == collections_link.href

    def test_get_collections_single_slash(self, requests_mock: Mocker) -> None:
        pc_root_text = read_data_file("planetary-computer-root.json")
        root_url = "http://pystac-client.test/"
        requests_mock.get(root_url, status_code=200, text=pc_root_text)
        api = Client.open(root_url)
        pc_collection_dict = read_data_file(
            "planetary-computer-aster-l1t-collection.json", parse_json=True
        )
        requests_mock.get(
            f"{root_url}collections",  # note the lack of the slash
            status_code=200,
            json={"collections": [pc_collection_dict], "links": []},
        )
        _ = next(api.get_collections())
        history = requests_mock.request_history
        assert len(history) == 2
        assert history[1].url == f"{root_url}collections"

    def test_custom_request_parameters(self, requests_mock: Mocker) -> None:
        pc_root_text = read_data_file("planetary-computer-root.json")
        pc_collection_dict = read_data_file(
            "planetary-computer-collection.json", parse_json=True
        )

        requests_mock.get(
            STAC_URLS["PLANETARY-COMPUTER"], status_code=200, text=pc_root_text
        )

        init_qp_name = "my-param"
        init_qp_value = "some-value"

        api = Client.open(
            STAC_URLS["PLANETARY-COMPUTER"], parameters={init_qp_name: init_qp_value}
        )
        assert api._stac_io is not None

        # Ensure that the Client will use the /collections endpoint and not fall back
        # to traversing child links.
        assert api._stac_io.conforms_to(ConformanceClasses.COLLECTIONS)

        # Get the /collections endpoint
        collections_link = api.get_single_link("data")
        assert collections_link is not None

        # Mock the request
        requests_mock.get(
            collections_link.href,
            status_code=200,
            json={"collections": [pc_collection_dict], "links": []},
        )

        # Make the collections request
        _ = next(api.get_collections())

        history = requests_mock.request_history
        assert len(history) == 2

        actual_qs = urlsplit(history[1].url).query
        actual_qp = parse_qs(actual_qs)

        # Check that the param from the init method is present
        assert init_qp_name in actual_qp
        assert len(actual_qp[init_qp_name]) == 1
        assert actual_qp[init_qp_name][0] == init_qp_value

    def test_custom_query_params_get_collections_propagation(
        self, requests_mock: Mocker
    ) -> None:
        """Checks that query params passed to the init method are added to requests for
        CollectionClients fetched from
        the /collections endpoint."""
        pc_root_text = read_data_file("planetary-computer-root.json")
        pc_collection_dict = read_data_file(
            "planetary-computer-collection.json", parse_json=True
        )

        requests_mock.get(
            STAC_URLS["PLANETARY-COMPUTER"], status_code=200, text=pc_root_text
        )

        init_qp_name = "my-param"
        init_qp_value = "some-value"

        client = Client.open(
            STAC_URLS["PLANETARY-COMPUTER"], parameters={init_qp_name: init_qp_value}
        )

        # Get the /collections endpoint
        collections_link = client.get_single_link("data")
        assert collections_link is not None

        # Mock the request
        requests_mock.get(
            collections_link.href,
            status_code=200,
            json={"collections": [pc_collection_dict], "links": []},
        )

        # Make the collections request
        collection = next(client.get_collections())

        # Mock the items endpoint
        items_link = collection.get_single_link("items")
        assert items_link is not None
        requests_mock.get(
            items_link.href,
            status_code=200,
            json={
                "type": "FeatureCollection",
                "stac_version": "1.0.0",
                "features": [],
                "links": [],
            },
        )

        # Make the items request
        _ = list(collection.get_items())

        history = requests_mock.request_history
        assert len(history) == 3

        actual_qs = urlsplit(history[2].url).query
        actual_qp = parse_qs(actual_qs)

        # Check that the query param from the root Client is present
        assert init_qp_name in actual_qp
        assert len(actual_qp[init_qp_name]) == 1
        assert actual_qp[init_qp_name][0] == init_qp_value

    def test_custom_query_params_get_collection_propagation(
        self, requests_mock: Mocker
    ) -> None:
        """Checks that query params passed to the init method are added to
        requests for CollectionClients fetched from the /collections endpoint."""
        pc_root_text = read_data_file("planetary-computer-root.json")
        pc_collection_dict = read_data_file(
            "planetary-computer-collection.json", parse_json=True
        )
        assert isinstance(pc_collection_dict, dict)
        pc_collection_id = pc_collection_dict["id"]

        requests_mock.get(
            STAC_URLS["PLANETARY-COMPUTER"], status_code=200, text=pc_root_text
        )

        init_qp_name = "my-param"
        init_qp_value = "some-value"

        client = Client.open(
            STAC_URLS["PLANETARY-COMPUTER"], parameters={init_qp_name: init_qp_value}
        )

        # Get the /collections endpoint
        collections_link = client.get_single_link("data")
        assert collections_link is not None
        collection_href = collections_link.href + "/" + pc_collection_id

        # Mock the request
        requests_mock.get(collection_href, status_code=200, json=pc_collection_dict)

        # Make the collections request
        collection = client.get_collection(pc_collection_id)
        assert collection is not None

        # Mock the items endpoint
        items_link = collection.get_single_link("items")
        assert items_link is not None
        requests_mock.get(
            items_link.href,
            status_code=200,
            json={
                "type": "FeatureCollection",
                "stac_version": "1.0.0",
                "features": [],
                "links": [],
            },
        )

        # Make the items request
        _ = list(collection.get_items())

        history = requests_mock.request_history
        assert len(history) == 3

        actual_qs = urlsplit(history[2].url).query
        actual_qp = parse_qs(actual_qs)

        # Check that the query param from the root Client is present
        assert init_qp_name in actual_qp
        assert len(actual_qp[init_qp_name]) == 1
        assert actual_qp[init_qp_name][0] == init_qp_value

    def test_get_collections_without_conformance(self, requests_mock: Mocker) -> None:
        """Checks that the "data" endpoint is used if the API published
        the Collections conformance class."""
        pc_root_dict = read_data_file("planetary-computer-root.json", parse_json=True)
        pc_collection_dict = read_data_file(
            "planetary-computer-aster-l1t-collection.json", parse_json=True
        )

        # Remove the collections conformance class
        pc_root_dict["conformsTo"].remove(
            "https://api.stacspec.org/v1.0.0-beta.1/collections"
        )

        # Remove all child links except for the collection that we are mocking
        pc_collection_href = next(
            link["href"]
            for link in pc_collection_dict["links"]
            if link["rel"] == "self"
        )
        pc_root_dict["links"] = [
            link
            for link in pc_root_dict["links"]
            if link["rel"] != "child" or link["href"] == pc_collection_href
        ]

        # Mock the root catalog
        requests_mock.get(
            STAC_URLS["PLANETARY-COMPUTER"], status_code=200, json=pc_root_dict
        )
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        assert api._stac_io is not None

        assert not api._stac_io.conforms_to(ConformanceClasses.COLLECTIONS)

        # Mock the collection
        requests_mock.get(pc_collection_href, status_code=200, json=pc_collection_dict)

        _ = next(api.get_collections())

        history = requests_mock.request_history
        assert len(history) == 2
        assert history[1].url == pc_collection_href

    def test_opening_a_collection(self) -> None:
        path = str(TEST_DATA / "planetary-computer-aster-l1t-collection.json")
        with pytest.raises(ClientTypeError):
            Client.open(path)


class TestAPISearch:
    @pytest.fixture(scope="function")  # type: ignore[misc]
    def api(self) -> Client:
        return Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))

    def test_search_conformance_error(self, api: Client) -> None:
        """Should raise a NotImplementedError if the API doesn't conform
        to the Item Search spec. Message should
        include information about the spec that was not conformed to."""
        # Set the conformance to only STAC API - Core
        assert api._stac_io is not None
        assert api._stac_io._conformance is not None
        api._stac_io._conformance = [api._stac_io._conformance[0]]

        with pytest.raises(NotImplementedError) as excinfo:
            api.search(limit=10, max_items=10, collections="mr-peebles")
        assert str(ConformanceClasses.ITEM_SEARCH) in str(excinfo.value)

    def test_no_search_link(self, api: Client) -> None:
        # Remove the search link
        api.remove_links("search")

        with pytest.raises(NotImplementedError) as excinfo:
            api.search(limit=10, max_items=10, collections="naip")
        assert "No link with rel=search could be found in this catalog" in str(
            excinfo.value
        )

    def test_no_conforms_to(self) -> None:
        with open(str(TEST_DATA / "planetary-computer-root.json")) as f:
            data = json.load(f)
        del data["conformsTo"]
        with TemporaryDirectory() as temporary_directory:
            path = os.path.join(temporary_directory, "catalog.json")
            with open(path, "w") as f:
                json.dump(data, f)
            api = Client.from_file(path)

        with pytest.raises(NotImplementedError) as excinfo:
            api.search(limit=10, max_items=10, collections="naip")
        assert "does not support search" in str(excinfo.value)

    def test_search(self, api: Client) -> None:
        results = api.search(
            bbox=[-73.21, 43.99, -73.12, 44.05],
            collections="naip",
            limit=10,
            max_items=20,
            datetime=[datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzutc()), None],
        )

        assert results._parameters == {
            "bbox": (-73.21, 43.99, -73.12, 44.05),
            "collections": ("naip",),
            "limit": 10,
            "datetime": "2020-01-01T00:00:00Z/..",
        }

    def test_json_search_link(self, api: Client) -> None:
        search_link = api.get_single_link(rel="search")
        assert search_link
        api.remove_links(rel="search")
        search_link.media_type = MediaType.JSON
        api.add_link(search_link)
        api.search(limit=1, max_items=1, collections="naip")

    @pytest.mark.vcr  # type: ignore[misc]
    def test_search_max_items_unlimited_default(self, api: Client) -> None:
        search = api.search(
            bbox=[-73.21, 43.99, -73.12, 45.05],
            collections="naip",
            datetime="2014-01-01/2020-12-31",
        )
        items = list(search.items())
        assert len(items) > 100


class MySign:
    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, x: Modifiable) -> None:
        self.call_count += 1


class TestSigning:
    @pytest.mark.vcr  # type: ignore[misc]
    def test_signing(self) -> None:
        sign = MySign()
        # sign is callable, but mypy keeps trying to interpret it as a "MySign" object.
        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"], modifier=sign)
        assert client.modifier is sign

        collection = client.get_collection("cil-gdpcir-cc0")
        assert collection
        assert isinstance(collection, CollectionClient)
        assert collection.modifier is sign  # type: ignore
        assert sign.call_count == 1

        collection.get_item("cil-gdpcir-INM-INM-CM5-0-ssp585-r1i1p1f1-day")
        assert sign.call_count == 2

        next(client.get_collections())
        assert sign.call_count == 3

        next(client.get_items())
        assert sign.call_count == 4

        next(client.get_all_items())
        assert sign.call_count == 5

        search = client.search(collections=["sentinel-2-l2a"], max_items=10)
        next(search.items_as_dicts())
        assert sign.call_count == 6

        next(search.items())
        assert sign.call_count == 7

        next(search.pages_as_dicts())
        assert sign.call_count == 8

        next(search.pages())
        assert sign.call_count == 9

        search.item_collection_as_dict()
        assert sign.call_count == 10

        search.item_collection()
        assert sign.call_count == 11

    @pytest.mark.vcr  # type: ignore[misc]
    def test_sign_with_return_warns(self) -> None:
        def modifier_ok(x: Any) -> Any:
            return x

        def modifier_bad(x: Any) -> Any:
            return 0

        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"], modifier=modifier_ok)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            client.get_collection("sentinel-2-l2a")

        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"], modifier=modifier_bad)
        with pytest.warns(IgnoredResultWarning):
            client.get_collection("sentinel-2-l2a")
