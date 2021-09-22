Usage
#####

PySTAC-Client (pystac-client) builds upon :ref:`~PySTAC<https://github.com/stac-utils/pystac>`_ library to add support
for STAC APIs in addition to static STACs. PySTAC-Client can be used with static or dynamic (i.e., API)
catalogs. Currently, pystac-client does not offer much in the way of additional functionality if using with
static catalogs, as the additional features are for support STAC API endpoints such as `search`. However,
in the future it is expected that pystac-client will offer additional convenience functions that may be 
useful for static and dynamic catalogs alike.

The most basic implementation of a STAC API is an endpoint that returns a valid STAC Catalog, but also contains
a ``"conformsTo"`` attribute that is a list of conformance URIs for the standards that the API supports.

This section is organized by the classes that are used, which mirror parent classes from PySTAC:

+------------------+------------+
| pystac-client    | pystac     |
+==================+============+
| Client           | Catalog    |
+------------------+------------+
| CollectionClient | Collection |
+------------------+------------+

The classes offer all of the same functions for accessing and traversing Catalogs as in PySTAC. The documentation
for pystac-client only includes new functions, it does not duplicate documentation for inherited functions.

Client
++++++

The :class:`pystac_client.Client` class is the main interface for working with services that conform to the STAC API spec.
This class inherits from the :class:`pystac.Catalog` class and in addition to the methods and attributes implemented by
a Catalog, it also includes convenience methods and attributes for:

* Checking conformance to various specs
* Querying a search endpoint (if the API conforms to the STAC API - Item Search spec)

The preferred way to interact with any STAC Catalog or API is to create an :class:`~pystac_client.Client` instance
with the ``pystac_client.Client.open` method on a root Catalog. This calls the :meth:`pystac.STACObject.from_file`
except properly configures conformance and IO for reading from remote servers.

The following code creates an instance by making a call to the Microsoft Planetary Computer root catalog.

.. code-block:: python

    >>> from pystac_client.Client import Client
    >>> api = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1')
    >>> api.title
    'microsoft-pc'

Some functions, such as ``Client.search`` will throw an error if the provided Catalog/API does
not support the required Conformance Class. In other cases, such as ``Client.get_collections``, API endpoints will be
used if the API conforms, otherwise it will fall back to default behavior provided by :class:`pystac.Catalog`.

Users may optionally provide an ``ignore_conformance`` argument when opening, in which case pystac-client will not check
for conformance and will assume this is a fully features API. This can cause unusual errors to be thrown if the API
does not in fact conform to the expected behavior.

In addition to the methods and attributes inherited from :class:`pystac.Catalog`, this class offers more efficient
methods (if used with an API) for getting collections and items, as well as a search capability, utilizing the
:class:`pystac_client.ItemSearch` class.

API Conformance
---------------

This library is intended to work with any STAC static catalog or STAC API. A static catalog will be usable more or less
the same as with PySTAC, except that pystac-client supports providing custom headers to API endpoints. (e.g., authenticating 
to an API with a token).

A STAC API is a STAC Catalog that is required to advertise it's capabilities in a `conformsTo` field and implements
the `STAC API - Core` spec along with other optional specifications:

* `STAC API - Core <https://github.com/radiantearth/stac-api-spec/tree/master/core>`__
* `STAC API - Item Search <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__
   * `Fields Extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/fields>`__
   * `Query Extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/query>`__
   * `Sort Extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/sort>`__
   * `Context Extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context>`__
   * `Filter Extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/filter>`__
* `STAC API - Features <https://github.com/radiantearth/stac-api-spec/tree/master/ogcapi-features>`__ (based on
  `OGC API - Features <https://www.ogc.org/standards/ogcapi-features>`__)

The :meth:`pystac_client.Client.conforms_to` method is used to check conformance against conformance classes (specs).
To check an API for support for a given spec, pass the `conforms_to` function the :class:`ConformanceClasses` attribute
as a parameter.

.. code-block:: python

    >>> from pystac_client import ConformanceClasses
    >>> api.conforms_to(ConformanceClasses.STAC_API_ITEM_SEARCH)
    True

CollectionClient
++++++++++++++++

STAC APIs may provide a curated list of catalogs and collections via their ``"links"`` attribute. Links with a ``"rel"``
type of ``"child"`` represent catalogs or collections provided by the API. Since :class:`~pystac_client.Client` instances are
also :class:`pystac.Catalog` instances, we can use the methods defined on that class to get collections:

.. code-block:: python

    >>> child_links = api.get_links('child')
    >>> len(child_links)
    12
    >>> first_child_link = api.get_single_link('child')
    >>> first_child_link.resolve_stac_object(api)
    >>> first_collection = first_child_link.target
    >>> first_collection.title
    'Landsat 8 C1 T1'

CollectionClient overrides the :meth:`pystac.Collection.get_items` method. PySTAC will get items by
iterating through all children until it gets to an `item` link. If the `CollectionClient` instance
contains an `items` link, this will instead iterate through items using the API endpoint instead:
`/collections/<collection_id>/items`. If no such link is present it will fall back to the
PySTAC Collection behavior.


ItemSearch
++++++++++

STAC API services may optionally implement a ``/search`` endpoint as describe in the  `STAC API - Item Search spec
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__. This endpoint allows clients to query
STAC Items across the entire service using a variety of filter parameters. See the `Query Parameter Table
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__ from that spec for
details on the meaning of each parameter.

The :meth:`pystac_client.Client.search` method provides an interface for making requests to a service's
"search" endpoint. This method returns a :class:`pystac_client.ItemSearch` instance.

.. code-block:: python

    >>> from pystac_client import API
    >>> api = API.from_file('https://eod-catalog-svc-prod.astraea.earth')
    >>> results = api.search(
    ...     bbox=[-73.21, 43.99, -73.12, 44.05],
    ...     datetime=['2019-01-01T00:00:00Z', '2019-01-02T00:00:00Z'],
    ...     max_items=5
    ... )

Instances of :class:`~pystac_client.ItemSearch` have 2 methods for iterating over results:

* :meth:`ItemSearch.get_item_collections <pystac_client.ItemSearch.item_collections>`: iterates over *pages* of results,
  yielding an :class:`~pystac.ItemCollection` for each page of results.
* :meth:`ItemSearch.get_items <pystac_client.ItemSearch.items>`: iterate over individual results, yielding a
  :class:`pystac.Item` instance for all items that match the search criteria.

In addition three additional convenience methods are provided:

* :meth:`ItemSearch.matched <pystac_client.ItemSearch.matched>`: returns the number of hits (items) for this search.
  Not all APIs support returning a total count, in which case a warning will be issued.
* :meth:`ItemSearch.matched <pystac_client.ItemSearch.get_all_items>`: Rather than return an iterator, this function will
  fetch all items and return them as a single :class:`~pystac.ItemCollection`.
* :meth:`ItemSearch.matched <pystac_client.ItemSearch.get_all_items_as_dict>`: Like `get_all_items` this fetches all items
  but returns them as a GeoJSON FeatureCollection dictionary rather than a PySTAC object. This can be more efficient if
  only a dictionary of the results is needed.

.. code-block:: python

    >>> for item in results.get_items():
    ...     print(item.id)
    S2B_OPER_MSI_L2A_TL_SGS__20190101T200120_A009518_T18TXP_N02.11
    MCD43A4.A2019010.h12v04.006.2019022234410
    MCD43A4.A2019009.h12v04.006.2019022222645
    MYD11A1.A2019002.h12v04.006.2019003174703
    MYD11A1.A2019001.h12v04.006.2019002165238

The :meth:`~pystac_client.ItemSearch.get_items` and related methods handle retrieval of successive pages of results 
by finding links with a ``"rel"`` type of ``"next"`` and parsing them to construct the next request. The default 
implementation of this ``"next"`` link parsing assumes that the link follows the spec for an extended STAC link as
described in the `STAC API - Item Search: Paging <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#paging>`__
section. See the :mod:`Paging <pystac_client.paging>` docs for details on how to customize this behavior.

Query Filter
------------

If the Catalog supports the `Query
extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/query>`__,
any Item property can also be included in the search. Rather than
requiring the JSON syntax the Query extension uses, pystac-client can use a
simpler syntax that it will translate to the JSON equivalent. Note
however that when the simple syntax is used it sends all property values
to the server as strings, except for ``gsd`` which it casts to
``float``. This means that if there are extensions in use with numeric
properties these will be sent as strings. Some servers may automatically
cast this to the appropriate data type, others may not.

The query filter will also accept complete JSON as per the specification.

::

  <property><operator><value>

  where operator is one of `>=`, `<=`, `>`, `<`, `=`

  Examples:
  eo:cloud_cover<10
  view:off_nadir<50
  platform=landsat-8

Any number of properties can be included, and each can be included more
than once to use additional operators.
