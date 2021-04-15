"""Base classes for implementing new extensions."""
from abc import ABC, abstractmethod

from pystac import Catalog, Collection, Item
from pystac.extensions import ExtensionError
from pystac.extensions.base import CatalogExtension, CollectionExtension, ItemExtension

from pystac_client.client import Client
from pystac_client.item_collection import ItemCollection
from pystac_client.item_search import ItemSearch


class ExtendedObject:
    """Maps :class:`pystac.STACObject` classes (API, Catalog, Collection and Item) and the
    :class:`~pystac_client.ItemSearch` class (which does not inherit from :class:`pystac.STACObject`) to extension classes
    (classes that implement one of :class:`APIExtension`, :class:`ItemSearchFragment`, :class:`ItemCollectionFragment`,
    :class:`CatalogExtension`, :class:`CollectionExtension`, or :class:`ItemCollection`). When an extension is
    registered it uses the registered list of ``ExtendedObjects`` to determine how to handle extending objects, e.g.
    when ``item.ext.label`` is called, it searches for the ``ExtendedObject`` associated with the label extension that
    maps :class:`~pystac.Item` to :class:`~pystac.extensions.label.LabelItemExt`.

    Parameters
    ----------
    stac_object_class : type
        The :class:`~pystac.STACObject` class that is being extended (may also be the
        :class:`~pystac_client.ItemSearch` class, which does not inherit from :class:`~pystac.STACObject`).
    extension_class : type
        The class of the extension (e.g. :class:`~pystac_client.extensions.context.ContextAPIExtension`)
    """
    def __init__(self, stac_object_class, extension_class):
        if stac_object_class is Client:
            if not issubclass(extension_class, APIExtension):
                raise ExtensionError(
                    "Classes extending API instances must inherit from APIExtension")
        if stac_object_class is ItemSearch:
            if not issubclass(extension_class, ItemSearchFragment):
                raise ExtensionError(
                    "Classes extending ItemSearch instances must inherit from ItemSearchExtension")
        if stac_object_class is ItemCollection:
            if not issubclass(extension_class, ItemCollectionFragment):
                raise ExtensionError(
                    "Classes extending ItemCollection instances must inherit from ItemCollectionExtension"
                )
        if stac_object_class is Catalog:  # pragma: no cover
            if not issubclass(extension_class, CatalogExtension):
                raise ExtensionError(
                    "Classes extending catalogs must inherit from CatalogExtension")
        if stac_object_class is Collection:  # pragma: no cover
            if not issubclass(extension_class, CollectionExtension):
                raise ExtensionError(
                    "Classes extending collections must inherit from CollectionExtension")
        if stac_object_class is Item:  # pragma: no cover
            if not issubclass(extension_class, ItemExtension):
                raise ExtensionError("Classes extending item must inherit from ItemExtension")

        self.stac_object_class = stac_object_class
        self.extension_class = extension_class


class ItemCollectionFragment(ABC):

    conformance = None
    """MUST be overwritten in the child class with a :class:`~pystac_client.conformance.ConformanceClass` instance
    that defines the conformance URIs associated with this extension."""
    @classmethod
    def _from_object(cls, stac_object):
        return cls.from_item_collection(stac_object)

    @classmethod
    @abstractmethod
    def from_item_collection(cls, item_collection):  # pragma: no cover
        """Creates an instance of the extension from an :class:`~pystac_client.ItemCollection` instance."""

    @classmethod
    @abstractmethod
    def _object_links(cls):  # pragma: no cover
        """Returns any object links added by this extension."""

    @classmethod
    def __init_subclass__(cls):
        if getattr(cls, 'conformance', None) is None:
            raise NotImplementedError(
                'Sub-classes of ItemCollectionFragment must implement conformance attribute.')


class ItemSearchFragment(ABC):

    conformance = None
    """MUST be overwritten in the child class with a :class:`~pystac_client.conformance.ConformanceClass` instance
    that defines the conformance URIs associated with this extension."""
    @classmethod
    def _from_object(cls, stac_object):
        return cls.from_item_search(stac_object)

    @classmethod
    @abstractmethod
    def from_item_search(cls, item_search):
        """Creates an instance of the extension from an :class:`~pystac_client.ItemSearch` instance."""

    @classmethod
    @abstractmethod
    def _object_links(cls):
        """Returns any object links added by this extension."""

    @classmethod
    def __init_subclass__(cls):
        if getattr(cls, 'conformance', None) is None:
            raise NotImplementedError(
                'Sub-classes of ItemSearchFragment must implement conformance attribute.')


class APIExtension(ABC):
    @classmethod
    def _from_object(cls, stac_object: Client):
        return cls.from_api(stac_object)

    @classmethod
    @abstractmethod
    def from_api(cls, api: Client):
        """Creates an instance of the extension from an :class:`~pystac_client.Client` instance."""

    @classmethod
    @abstractmethod
    def _object_links(cls):
        """Returns any object links added by this extension."""

    @classmethod
    def __init_subclass__(cls):
        if getattr(cls, 'conformance', None) is None:
            raise NotImplementedError(
                'Sub-classes of APIExtension must implement conformance attribute.')

    conformance = None
    """MUST be overwritten in the child class with a :class:`~pystac_client.conformance.ConformanceClass` instance
    that defines the conformance URIs associated with this extension."""
