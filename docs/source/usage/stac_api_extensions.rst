API Extensions
==============

Overview
--------

The STAC API spec defines a number of `API Extensions
<https://github.com/radiantearth/stac-api-spec/blob/master/extensions.md>`__ that a service may implement to extend its
functionality. Currently, the scope of the API Extensions is limited to Item Search requests and the STAC API - Features
``/items`` endpoint, but future extensions could extend this scope to other API components.

Unlike `STAC Core Extensions <https://github.com/radiantearth/stac-spec/tree/master/extensions>`__, API extensions are
not published within the ``"stac_extensions"`` attribute of a STAC object. Instead, they are published as conformance
URIs in the ``"conformsTo"`` attribute of the service's landing page. Because of this, API Extensions are handled
separately from Core Extensions in ``pystac_api``. Core Extension functionality is still available through the ``ext``
property of :class:`pystac.STACObject` instances thanks to ``pystac``, and all API Extensions functionality is
available through an analogous ``api_ext`` property on those objects. The ``api_ext`` property is also available on
:class:`~pystac_api.ItemSearch` instances even though they are not STAC objects themselves.

The following table indicates support in ``pystac_api`` for the known community API extensions defined
`here <https://github.com/radiantearth/stac-api-spec/blob/master/extensions.md#list-of-community-extensions>`__.

=================================   ===========
        Extension Name                Support
=================================   ===========
Fields                              Coming Soon
Query                               Coming Soon
Context                             Supported
Sort                                Coming Soon
Transaction                         Planned
Items and Collections API Version   Planned
=================================   ===========

Check Conformance
+++++++++++++++++

:class:`~pystac_api.API`, :class:`~pystac_api.ItemSearch`, and :class`~pystac_api.ItemCollection` instances all have
an ``api_ext`` property that is an :class:`~pystac_api.stac_api_object.APIExtensionIndex` instance. You can use the
:meth:`~pystac_api.stac_api_object.APIExtensionIndex.implements` method to check whether the service implements the
given extension using a context identifier:

.. code-block:: python

    >>> from pystac_api import API, APIExtensions
    >>> api = API.from_file(...)
    >>> api.api_ext.implements(APIExtensions.CONTEXT)
    True

.. note::

    STAC API extensions do not have well-defined identifiers in the same way that Core Extensions do (e.g. ``label``).
    This library defines its own identifiers for these extensions in the :obj:`pystac_api.APIExtensions` variable. These
    identifiers are generally the lower-cased extension name, but it is recommended to use the attributes of this
    variable when checking implementation.

Context Extension
-----------------

This library supports interacting with the attributes of the `Context Object
<https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context#context-object>`__ in an `Item Collection
<https://github.com/radiantearth/stac-api-spec/blob/master/fragments/itemcollection/README.md>`__ for services that
implement the Context Extension. The implementation extends :class:`~pystac_api.API`, :class:`~pystac_api.ItemSearch`, and
:class:`pystac_api.ItemCollection` instances.

``API`` Instances
+++++++++++++++++

The :class:`~pystac_api.extensions.context.ContextAPIExtension` class extends :class:`~pystac_api.API` instances to
enable checking conformance with this extension:

.. code-block:: python

    >>> from pystac_api import API, APIExtensions
    >>> api = API.from_file('https://eod-catalog-svc-prod.astraea.earth')
    >>> api.api_ext.implements(APIExtensions.CONTEXT)
    True

No other functionality is added to :class:`~pystac_api.API` instances as part of this extension.

``ItemSearch`` Instances
++++++++++++++++++++++++

The :class:`~pystac_api.extensions.context.ContextItemSearchFragment` class extends :class:`~pystac_api.ItemSearch`
instances to enable checking conformance with this extension:

.. code-block:: python

    >>> results = api.search(
    ...     bbox=(-73.21, 43.99, -73.12, 44.05),
    ...     collections='naip',
    ... )
    >>> results.api_ext.implements(APIExtensions.CONTEXT)
    True

No other functionality is added to :class:`~pystac_api.ItemSearch` instances as part of this extension.

``ItemCollection`` Instances
++++++++++++++++++++++++++++

The :class:`~pystac_api.extensions.context.ContextItemCollectionFragment` class extends
:class:`~pystac_api.ItemCollection` instances to enable checking conformance with this extension and access to the
``limit``, ``matched``, and ``returned`` elements of a `Context Object
<https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context#context-object>`__:

.. code-block:: python

    >>> first_page = next(results.item_collections())
    >>> first_page.api_ext.implements(APIExtensions.CONTEXT)
    True
    >>> first_page.api_ext.context.returned
    10
    >>> first_page.api_ext.context.limit
    10
    >>> first_page.api_ext.context.matched
    30

