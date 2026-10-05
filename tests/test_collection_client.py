from typing import Any

import pystac
import pytest
from requests_mock import Mocker

from pystac_client import CollectionClient
from pystac_client.client import Client
from pystac_client.exceptions import APIError
from pystac_client.warnings import DoesNotConformTo, FallbackToPystac, MissingLink

from .helpers import STAC_URLS, read_data_file

TRANSACTION_URI = (
    "https://api.stacspec.org/v1.0.0/ogcapi-features/extensions/transaction"
)


class TestCollectionClient:
    @pytest.mark.vcr
    def test_instance(self) -> None:
        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        collection = client.get_collection("aster-l1t")

        assert isinstance(collection, CollectionClient)
        assert str(collection) == "<CollectionClient id=aster-l1t>"

    @pytest.mark.vcr
    def test_get_items(self) -> None:
        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        collection = client.get_collection("aster-l1t")
        assert collection is not None
        for item in collection.get_items():
            assert item.collection_id == collection.id
            return

    @pytest.mark.vcr
    def test_get_items_with_ids(self) -> None:
        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        collection = client.get_collection("aster-l1t")
        ids = [
            "AST_L1T_00312272006020322_20150518201805",
            "AST_L1T_00312272006020313_20150518201753",
            "AST_L1T_00312272006020304_20150518201753",
        ]
        assert collection is not None
        for item in collection.get_items(*ids):
            assert item.collection_id == collection.id
            assert item.id in ids

    @pytest.mark.vcr
    def test_get_item(self) -> None:
        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        collection = client.get_collection("aster-l1t")
        assert collection is not None
        item = collection.get_item("AST_L1T_00312272006020322_20150518201805")
        assert item
        assert item.id == "AST_L1T_00312272006020322_20150518201805"

        item = collection.get_item("for-sure-not-a-real-id")
        assert item is None

    @pytest.mark.vcr
    def test_get_item_with_item_search(self) -> None:
        client = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        collection = client.get_collection("aster-l1t")
        assert collection is not None

        client.set_conforms_to(
            [
                "https://api.stacspec.org/v1.0.0-rc.2/core",
                "https://api.stacspec.org/v1.0.0-rc.2/item-search",
            ]
        )

        item = collection.get_item("AST_L1T_00312272006020322_20150518201805")
        assert item
        assert item.id == "AST_L1T_00312272006020322_20150518201805"

        item = collection.get_item("for-sure-not-a-real-id")
        assert item is None
        with pytest.warns(FallbackToPystac):
            item = collection.get_item(
                "AST_L1T_00312272006020322_20150518201805", recursive=True
            )
        assert item
        assert item.id == "AST_L1T_00312272006020322_20150518201805"

    @pytest.mark.vcr
    def test_get_queryables(self) -> None:
        api = Client.open(STAC_URLS["PLANETARY-COMPUTER"])
        collection_client = api.get_collection("landsat-c2-l2")
        assert collection_client is not None
        assert isinstance(collection_client, CollectionClient)
        with pytest.warns(MissingLink, match="/queryables"):
            result = collection_client.get_queryables()
        assert "instrument" in result["properties"]
        assert "landsat:scene_id" in result["properties"]


class TestTransactions:
    root_url = STAC_URLS["PLANETARY-COMPUTER"]
    collection_url = f"{root_url}/collections/aster-l1t"
    items_url = f"{collection_url}/items"

    def _open_collection(
        self, requests_mock: Mocker, transaction: bool = True, **client_kwargs: Any
    ) -> CollectionClient:
        root = read_data_file("planetary-computer-root.json", parse_json=True)
        if transaction:
            root["conformsTo"].append(TRANSACTION_URI)
        requests_mock.get(self.root_url, status_code=200, json=root)
        requests_mock.get(
            self.collection_url,
            status_code=200,
            text=read_data_file("planetary-computer-aster-l1t-collection.json"),
        )
        client = Client.open(self.root_url, **client_kwargs)
        collection = client.get_collection("aster-l1t")
        assert isinstance(collection, CollectionClient)
        return collection

    def _item_dict(self) -> dict[str, Any]:
        item: dict[str, Any] = read_data_file("sample-item.json", parse_json=True)
        item["collection"] = "aster-l1t"
        return item

    def test_create_item(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock)
        item_dict = self._item_dict()
        # servers may add fields to the created item
        response = {**item_dict, "properties": {**item_dict["properties"], "x": 1}}
        requests_mock.post(self.items_url, status_code=201, json=response)

        item = collection.create_item(pystac.Item.from_dict(item_dict))

        request = requests_mock.request_history[-1]
        assert request.method == "POST"
        assert request.url == self.items_url
        assert request.json()["id"] == item_dict["id"]
        assert isinstance(item, pystac.Item)
        assert item.id == item_dict["id"]
        assert item.properties["x"] == 1
        assert item.get_self_href() == f"{self.items_url}/{item_dict['id']}"

    @pytest.mark.parametrize("response", ["", '{"status": "created"}'])
    def test_create_item_from_dict_sets_collection(
        self, requests_mock: Mocker, response: str
    ) -> None:
        collection = self._open_collection(requests_mock)
        item_dict = self._item_dict()
        del item_dict["collection"]
        requests_mock.post(self.items_url, status_code=201, text=response)

        item = collection.create_item(item_dict)

        assert requests_mock.request_history[-1].json()["collection"] == "aster-l1t"
        assert "collection" not in item_dict
        assert item.id == item_dict["id"]
        assert item.collection_id == "aster-l1t"

    def test_create_item_wrong_collection(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock)
        item_dict = self._item_dict()
        item_dict["collection"] = "other"

        with pytest.raises(ValueError, match="other"):
            collection.create_item(item_dict)

        assert requests_mock.request_history[-1].method == "GET"

    def test_create_item_uses_stac_api_io(self, requests_mock: Mocker) -> None:
        """Checks that headers and request modifiers apply to transactions."""

        def add_auth(request: Any) -> None:
            request.headers["Authorization"] = "Bearer token"

        collection = self._open_collection(
            requests_mock, headers={"x-custom": "value"}, request_modifier=add_auth
        )
        requests_mock.post(self.items_url, status_code=201, json=self._item_dict())

        collection.create_item(self._item_dict())

        request = requests_mock.request_history[-1]
        assert request.headers["x-custom"] == "value"
        assert request.headers["Authorization"] == "Bearer token"

    @pytest.mark.parametrize("status_code", [400, 401, 403, 409, 500])
    def test_create_item_error(self, requests_mock: Mocker, status_code: int) -> None:
        collection = self._open_collection(requests_mock)
        requests_mock.post(self.items_url, status_code=status_code, text="nope")

        with pytest.raises(APIError, match="nope") as excinfo:
            collection.create_item(self._item_dict())

        assert excinfo.value.status_code == status_code

    def test_create_item_does_not_conform(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock, transaction=False)

        with pytest.raises(DoesNotConformTo, match="TRANSACTION"):
            collection.create_item(self._item_dict())

    def test_update_item(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock)
        item_dict = self._item_dict()
        item_url = f"{self.items_url}/{item_dict['id']}"
        requests_mock.put(item_url, status_code=204)

        item = collection.update_item(item_dict)

        request = requests_mock.request_history[-1]
        assert request.method == "PUT"
        assert request.url == item_url
        assert request.json()["id"] == item_dict["id"]
        assert item.id == item_dict["id"]

    def test_patch_item(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock)
        item_dict = self._item_dict()
        item_url = f"{self.items_url}/{item_dict['id']}"
        requests_mock.patch(item_url, status_code=200, json=item_dict)

        item = collection.patch_item(item_dict["id"], {"properties": {"x": 1}})

        request = requests_mock.request_history[-1]
        assert request.method == "PATCH"
        assert request.url == item_url
        assert request.json() == {"properties": {"x": 1}}
        assert item is not None
        assert item.get_self_href() == item_url

    def test_patch_item_no_body(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock)
        requests_mock.patch(f"{self.items_url}/an-item", status_code=204)

        assert collection.patch_item("an-item", {"properties": {"x": 1}}) is None

    def test_delete_item(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock)
        item_url = f"{self.items_url}/an-item"
        requests_mock.delete(item_url, status_code=204)

        collection.delete_item("an-item")

        request = requests_mock.request_history[-1]
        assert request.method == "DELETE"
        assert request.url == item_url

    def test_delete_item_encodes_id(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock)
        item_url = f"{self.items_url}/a%2Fb%23c"
        requests_mock.delete(item_url, status_code=204)

        collection.delete_item("a/b#c")

        assert requests_mock.request_history[-1].url == item_url

    @pytest.mark.parametrize("status_code", [401, 403, 404, 500])
    def test_delete_item_error(self, requests_mock: Mocker, status_code: int) -> None:
        collection = self._open_collection(requests_mock)
        requests_mock.delete(
            f"{self.items_url}/an-item",
            status_code=status_code,
            json={"detail": "nope"},
        )

        with pytest.raises(APIError) as excinfo:
            collection.delete_item("an-item")

        assert excinfo.value.status_code == status_code

    def test_delete_item_does_not_conform(self, requests_mock: Mocker) -> None:
        collection = self._open_collection(requests_mock, transaction=False)

        with pytest.raises(DoesNotConformTo, match="TRANSACTION"):
            collection.delete_item("an-item")
