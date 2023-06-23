import json
import os.path
import warnings
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import Any, Dict
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
from pystac_client.exceptions import APIError
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import (
    DoesNotConformTo,
    FallbackToPystac,
    MissingLink,
    NoConformsTo,
    strict,
)

from .helpers import STAC_URLS, TEST_DATA, read_data_file


class TestAPI:
    @pytest.mark.vcr
    def test_instance(self) -> None:
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])

        # An API instance is also a Catalog instance
        assert isinstance(api, pystac.Catalog)

        assert str(api) == "<Client id=microsoft-pc>"

    @pytest.mark.vcr
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

    @pytest.mark.vcr
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

        assert api.conforms_to(ConformanceClasses.COLLECTIONS)

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
        api.remove_links("data")
        with pytest.warns(MissingLink, match="No link with rel='data'"):
            _ = next(api.get_collections())
        history = requests_mock.request_history
        assert len(history) == 2
        assert history[1].url == f"{root_url}collections"

    def test_keep_trailing_slash_on_root(self, requests_mock: Mocker) -> None:
        pc_root_text = read_data_file("planetary-computer-root.json")
        root_url = "http://pystac-client.test/"
        requests_mock.get(root_url, status_code=200, text=pc_root_text)
        client = Client.open(root_url)
        self_href = client.get_self_href()
        assert self_href
        assert self_href.endswith("/")

    def test_fall_back_to_data_link_for_collections(
        self, requests_mock: Mocker
    ) -> None:
        pc_root_text = read_data_file("planetary-computer-root.json")
        root_url = "http://pystac-client.test/"
        requests_mock.get(root_url, status_code=200, text=pc_root_text)
        api = Client.open(root_url)
        api.set_self_href(None)
        pc_collection_dict = read_data_file(
            "planetary-computer-aster-l1t-collection.json", parse_json=True
        )
        requests_mock.get(
            # the href of the data link
            "https://planetarycomputer.microsoft.com/api/stac/v1/collections",
            status_code=200,
            json={"collections": [pc_collection_dict], "links": []},
        )
        _ = next(api.get_collections())
        history = requests_mock.request_history
        assert len(history) == 2
        assert (
            history[1].url
            == "https://planetarycomputer.microsoft.com/api/stac/v1/collections"
        )

    def test_build_absolute_href_from_data_link(self, requests_mock: Mocker) -> None:
        pc_root = read_data_file("planetary-computer-root.json", parse_json=True)
        assert isinstance(pc_root, Dict)
        for link in pc_root["links"]:
            if link["rel"] == "data":
                link["href"] = "./collections"
        root_url = "http://pystac-client.test/"
        requests_mock.get(root_url, status_code=200, text=json.dumps(pc_root))
        api = Client.open(root_url)
        api.set_self_href(None)
        api.add_link(
            pystac.Link(
                rel="self",
                target="https://planetarycomputer.microsoft.com/api/stac/v1/",
            )
        )
        pc_collection_dict = read_data_file(
            "planetary-computer-aster-l1t-collection.json", parse_json=True
        )
        requests_mock.get(
            # the href of the data link
            "https://planetarycomputer.microsoft.com/api/stac/v1/collections",
            status_code=200,
            json={"collections": [pc_collection_dict], "links": []},
        )
        _ = next(api.get_collections())
        history = requests_mock.request_history
        assert len(history) == 2
        assert (
            history[1].url
            == "https://planetarycomputer.microsoft.com/api/stac/v1/collections"
        )

    def test_error_if_no_self_href_or_data_link(self, requests_mock: Mocker) -> None:
        pc_root = read_data_file("planetary-computer-root.json", parse_json=True)
        assert isinstance(pc_root, Dict)
        pc_root["links"] = [link for link in pc_root["links"] if link["rel"] != "data"]
        root_url = "http://pystac-client.test/"
        requests_mock.get(root_url, status_code=200, text=json.dumps(pc_root))
        api = Client.open(root_url)
        api.set_self_href(None)
        with pytest.warns(MissingLink, match="No link with rel='data'"):
            with pytest.raises(ValueError, match="does not have a self_href set"):
                _ = api.get_collection("an-id")

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

        # Ensure that the Client will use the /collections endpoint and not fall back
        # to traversing child links.
        assert api.conforms_to(ConformanceClasses.COLLECTIONS)

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

    def test_get_collections_without_conformance_fallsback_to_pystac(
        self, requests_mock: Mocker
    ) -> None:
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

        assert api.has_conforms_to()
        assert not api.conforms_to(ConformanceClasses.COLLECTIONS)
        assert not api.conforms_to(ConformanceClasses.FEATURES)

        # Mock the collection
        requests_mock.get(pc_collection_href, status_code=200, json=pc_collection_dict)

        with pytest.warns(DoesNotConformTo, match="COLLECTIONS, FEATURES"):
            _ = next(api.get_collections())

        history = requests_mock.request_history
        assert len(history) == 2

    def test_opening_a_collection(self) -> None:
        path = str(TEST_DATA / "planetary-computer-aster-l1t-collection.json")
        with pytest.raises(ClientTypeError):
            Client.open(path)

    def test_headers_with_custom_stac_io(self, requests_mock: Mocker) -> None:
        pc_root_dict = read_data_file("planetary-computer-root.json", parse_json=True)
        requests_mock.get(
            STAC_URLS["PLANETARY-COMPUTER"],
            status_code=200,
            json=pc_root_dict,
            request_headers={"ski": "pow", "shred": "gnar"},
        )
        stac_io = StacApiIO(headers={"ski": "pow"})
        _ = Client.open(
            STAC_URLS["PLANETARY-COMPUTER"], headers={"shred": "gnar"}, stac_io=stac_io
        )


class TestAPISearch:
    @pytest.fixture(scope="function")
    def api(self) -> Client:
        return Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))

    def test_search_conformance_error(self, api: Client) -> None:
        # Remove item search conformance
        api.remove_conforms_to("ITEM_SEARCH")

        with strict():
            with pytest.raises(DoesNotConformTo, match="ITEM_SEARCH"):
                api.search(limit=10, max_items=10, collections="mr-peebles")

    def test_no_search_link(self, api: Client) -> None:
        # Remove the search link
        api.remove_links("search")

        with strict():
            with pytest.raises(
                MissingLink,
                match="No link with rel='search' could be found on this Client",
            ):
                api.search(limit=10, max_items=10, collections="naip")

    def test_no_conforms_to(self) -> None:
        with open(str(TEST_DATA / "planetary-computer-root.json")) as f:
            data = json.load(f)
        del data["conformsTo"]
        with TemporaryDirectory() as temporary_directory:
            path = os.path.join(temporary_directory, "catalog.json")
            with open(path, "w") as f:
                json.dump(data, f)
            api = Client.from_file(path)

        with strict():
            with pytest.raises(DoesNotConformTo, match="ITEM_SEARCH"):
                api.search(limit=10, max_items=10, collections="naip")

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

    @pytest.mark.vcr
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
    @pytest.mark.vcr
    def test_signing(self) -> None:
        sign = MySign()
        # sign is callable, but mypy keeps trying to interpret it as a "MySign" object.
        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"], modifier=sign)
        assert client.modifier is sign

        collection = client.get_collection("cil-gdpcir-cc0")
        assert collection
        assert isinstance(collection, CollectionClient)
        assert collection.modifier is sign
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

    @pytest.mark.vcr
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


class TestQueryables:
    @pytest.mark.vcr
    def test_get_queryables(self) -> None:
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        with pytest.warns(MissingLink, match="queryables"):
            result = api.get_queryables()
        assert "properties" in result
        assert "id" in result["properties"]

    @pytest.mark.vcr
    def test_get_queryables_collections(self) -> None:
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        with pytest.warns(MissingLink, match="queryables"):
            col = api.get_collection("3dep-seamless")
            assert isinstance(col, CollectionClient)
            tdep_seamless_props = col.get_queryables()["properties"]
            col = api.get_collection("fia")
            assert isinstance(col, CollectionClient)
            fia_props = col.get_queryables()["properties"]
            result = api.get_merged_queryables(["fia", "3dep-seamless"])
        assert "properties" in result
        assert "id" in result["properties"]
        assert set(fia_props.keys()).issubset(result["properties"])
        assert set(tdep_seamless_props.keys()).issubset(result["properties"])

    def test_get_queryables_errors(self, requests_mock: Mocker) -> None:
        pc_root_text = read_data_file("planetary-computer-root.json")
        root_url = "http://pystac-client.test/"
        requests_mock.get(root_url, status_code=200, text=pc_root_text)
        api = Client.open(root_url)
        with pytest.raises(DoesNotConformTo, match="FILTER"):
            api.get_queryables()

        assert api._stac_io is not None
        api.add_conforms_to("FILTER")
        self_href = api.get_self_href()
        api.set_self_href(None)
        with pytest.warns(MissingLink, match="queryables"):
            with pytest.raises(ValueError, match="does not have a self_href set"):
                api.get_queryables()

        api.set_self_href(self_href)
        api._stac_io = None
        with pytest.warns(MissingLink, match="queryables"):
            with pytest.raises(APIError, match="API access is not properly configured"):
                api.get_queryables()


class TestConformsTo:
    def test_ignore_conformance_is_deprecated_and_noop(self) -> None:
        with pytest.warns(
            FutureWarning, match="`ignore_conformance` option is deprecated"
        ):
            client = Client.open(
                str(TEST_DATA / "planetary-computer-root.json"),
                ignore_conformance=True,
            )
        assert client.has_conforms_to()
        assert client.conforms_to(ConformanceClasses.CORE)

    def test_set_conforms_to_using_list_of_uris(self) -> None:
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        client.set_conforms_to(["https://api.stacspec.org/v1.0.0-rc.2/core"])

        assert client.conforms_to(ConformanceClasses.CORE)

    def test_add_and_remove_conforms_to_by_string(self) -> None:
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))

        client.remove_conforms_to("core")
        assert not client.conforms_to(ConformanceClasses.CORE)

        client.add_conforms_to("core")
        assert client.conforms_to("CORE")

    def test_clear_all_conforms_to(self) -> None:
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        client.clear_conforms_to()
        assert not client.has_conforms_to()

    def test_empty_conforms_to(self) -> None:
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        client.set_conforms_to([])
        assert client.has_conforms_to(), "The conformsTo field should still exist"

        assert not client.conforms_to(ConformanceClasses.CORE)
        assert not client.conforms_to(ConformanceClasses.ITEM_SEARCH)

    def test_no_conforms_to_falls_back_to_pystac(self) -> None:
        client = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        client.clear_conforms_to()

        with strict():
            with pytest.raises(FallbackToPystac):
                next(client.get_collections())

    @pytest.mark.vcr
    def test_changing_conforms_to_changes_behavior(self) -> None:
        with pytest.warns(NoConformsTo):
            client = Client.open("https://earth-search.aws.element84.com/v0")

        with pytest.warns(FallbackToPystac):
            next(client.get_collections())

        client.add_conforms_to("COLLECTIONS")

        with pytest.warns(MissingLink, match="rel='data'"):
            next(client.get_collections())


@pytest.mark.vcr
def test_collections_are_clients() -> None:
    # https://github.com/stac-utils/pystac-client/issues/548
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1/",
    )
    item = catalog.get_collection("cil-gdpcir-cc-by").get_item(
        "cil-gdpcir-NUIST-NESM3-ssp585-r1i1p1f1-day"
    )
    assert item
    item.get_collection()
