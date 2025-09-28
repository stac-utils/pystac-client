import pytest

from pystac_client import Client
from pystac_client.warnings import DoesNotConformTo, ignore, strict

from .helpers import TEST_DATA


class TestWarningContextManagers:
    @pytest.mark.filterwarnings("error")
    def test_ignore_context_manager(self) -> None:
        """Test that ignore() context manager suppresses warnings."""
        api = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        api.remove_conforms_to("COLLECTION_SEARCH")

        # This should emit a DoesNotConformTo warning, but ignore() should suppress it
        with ignore():
            api.collection_search(limit=10, max_collections=10, q="test")

    @pytest.mark.filterwarnings("error")
    def test_strict_context_manager(self) -> None:
        """Test that strict() context manager converts warnings to exceptions."""
        api = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        api.remove_conforms_to("COLLECTION_SEARCH")

        # This should raise DoesNotConformTo as an exception
        with strict():
            with pytest.raises(DoesNotConformTo, match="COLLECTION_SEARCH"):
                api.collection_search(limit=10, max_collections=10, q="test")

    def test_ignore_context_manager_cleanup(self) -> None:
        """Test that ignore() properly restores warning filters after exit."""
        api = Client.from_file(str(TEST_DATA / "planetary-computer-root.json"))
        api.remove_conforms_to("COLLECTION_SEARCH")

        # Test that warnings are suppressed inside the context
        with ignore():
            api.collection_search(limit=10, max_collections=10, q="test")

        # Test that warnings are restored after exiting the context
        # Use strict() to ensure warnings become exceptions
        with strict():
            with pytest.raises(DoesNotConformTo, match="COLLECTION_SEARCH"):
                api.collection_search(limit=10, max_collections=10, q="test")
