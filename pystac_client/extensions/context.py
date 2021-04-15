"""Implementation of the `STAC API Context Extension
<https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context>`__"""
from typing import Optional

from pystac.extensions.base import ExtensionDefinition

from pystac_client import Client, APIExtensions, ConformanceClasses
from pystac_client.extensions import base
from pystac_client.item_collection import ItemCollection


class ContextItemCollectionExtension(base.ItemCollectionFragment):
    """Implements the `STAC API Context Extension
    <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context>`__ for
    :class:`~pystac_client.ItemCollection` instances.

    Enables retrieving the number of returned items in the given page, as well as the page size limit and total number
    of items matched, if the services provides those values.

    Examples
    --------

    >>> from pystac_client import Client
    >>> catalog = Client.from_file(...)
    >>> results = catalog.search(bbox=..., datetime=..., ...)
    >>> for i, page in enumerate(results.item_collections()):
    ...     print(f'Page {i + 1}:')
    ...     print(f'\tMatched: {page.api_ext.context.matched}')
    ...     print(f'\tReturned: {page.api_ext.context.returned}')
    ...     print(f'\tLimit: {page.api_ext.context.limit}')
    Page 1:
        Matched: 37
        Returned: 30
        Limit: 30
    Page 2:
        Matched: 37
        Returned: 7
        Limit: 30

    """
    conformance = ConformanceClasses.STAC_API_ITEM_SEARCH_CONTEXT_EXT

    def __init__(self, item_collection):
        self.item_collection = item_collection

    @classmethod
    def from_item_collection(cls, item_collection):
        return cls(item_collection)

    @classmethod
    def _object_links(cls):
        return []

    @property
    def limit(self) -> Optional[int]:
        """The value of the ``limit`` element as defined in the
        `Context Object <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context#context-object>`__
        documentation."""
        return self.item_collection.extra_fields['context'].get('limit')

    @property
    def returned(self) -> int:
        """The value of the ``returned`` element as defined in the
        `Context Object <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context#context-object>`__
        documentation."""
        return self.item_collection.extra_fields['context']['returned']

    @property
    def matched(self) -> Optional[int]:
        """The value of the ``matched`` element as defined in the
        `Context Object <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context#context-object>`__
        documentation."""
        return self.item_collection.extra_fields['context'].get('matched')


class ContextAPIExtension(base.APIExtension):
    """Implements the `STAC API Context Extension
    <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context>`__ for :class:`~pystac_client.API`
    instances.

    This extension class enables checking for implementation of the Context Extension on :class:`~pystac_client.API`
    objects as show below, but otherwise provides no new behavior for that class.

    Examples
    --------
    Returns ``True`` if the API landing page contains any of the
    :class:`~pystac_client.conformance.STAC_API_ITEM_SEARCH_CONTEXT_EXT` conformance URIs in its ``"conformsTo"``
    attribute.

    >>> from pystac_client import Client, ConformanceClasses
    >>> api = Client.from_file(...)
    >>> api.api_ext.implements(ConformanceClasses.STAC_API_ITEM_SEARCH_CONTEXT_EXT)
    True
    """

    conformance = ConformanceClasses.STAC_API_ITEM_SEARCH_CONTEXT_EXT
    """See the :class:`~pystac_client.conformance.STAC_API_ITEM_SEARCH_CONTEXT_EXT` for valid conformance URIs."""
    def __init__(self, api: Client):
        self.api = api

    @classmethod
    def from_api(cls, api: Client):
        return cls(api)

    @classmethod
    def _object_links(cls):
        return []


CONTEXT_EXTENSION_DEFINITION = ExtensionDefinition(APIExtensions.CONTEXT, [
    base.ExtendedObject(Client, ContextAPIExtension),
    base.ExtendedObject(ItemCollection, ContextItemCollectionExtension)
])
