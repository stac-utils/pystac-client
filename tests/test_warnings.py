import pytest

from pystac_client import Client
from pystac_client.warnings import ignore

from .helpers import TEST_DATA


@pytest.mark.filterwarnings("error")
def test_ignore() -> None:
    api = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
    api.remove_conforms_to("COLLECTION_SEARCH")
    with ignore():
        api.collection_search(limit=10, max_collections=10, q="test")
