import pytest
from pystac.extensions import ExtensionError

from pystac_client import Client, ItemCollection, ItemSearch
from pystac_client.extensions.base import (
    APIExtension,
    ExtendedObject,
    ItemCollectionFragment,
    ItemSearchFragment,
)


class TestExtendedObject:
    def test_wrong_class_exceptions(self):
        """Should raise exceptions if we try to extend the wrong class for a given extension"""
        with pytest.raises(ExtensionError):
            ExtendedObject(Client, ItemCollectionFragment)

        with pytest.raises(ExtensionError):
            ExtendedObject(ItemCollection, ItemSearchFragment)

        with pytest.raises(ExtensionError):
            ExtendedObject(ItemSearch, APIExtension)


class TestAbstractClasses:
    def test_api_conformance_constraint(self):
        with pytest.raises(NotImplementedError) as excinfo:

            class BogusExtension(APIExtension):
                """Does not implement the required conformance attribute"""
                @classmethod
                def from_api(cls, api):
                    pass

                @classmethod
                def _object_links(cls):
                    pass

        assert 'must implement conformance attribute' in str(excinfo)

    def test_item_search_conformance_constraint(self):
        with pytest.raises(NotImplementedError) as excinfo:

            class BogusFragment(ItemSearchFragment):
                """Does not implement the required conformance attribute"""
                @classmethod
                def from_item_search(cls, item_search):
                    pass

                @classmethod
                def _object_links(cls):
                    pass

        assert 'must implement conformance attribute' in str(excinfo)

    def test_item_collection_conformance_constraint(self):
        with pytest.raises(NotImplementedError) as excinfo:

            class BogusFragment(ItemCollectionFragment):
                """Does not implement the required conformance attribute"""
                @classmethod
                def from_item_collection(cls, item_collection):
                    pass

                @classmethod
                def _object_links(cls):
                    pass

        assert 'must implement conformance attribute' in str(excinfo)
