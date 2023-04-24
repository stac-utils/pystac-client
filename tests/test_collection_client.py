import pytest

from pystac_client import CollectionClient
from pystac_client.client import Client
from pystac_client.warnings import FallbackToPystac, MissingLink

from .helpers import STAC_URLS


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
