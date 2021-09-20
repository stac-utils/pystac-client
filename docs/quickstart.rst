
The most basic implementation of a STAC API is an endpoint that returns a valid STAC Catalog, along 
with a ``"conformsTo"`` attribute that is a list of conformance URIs for the standards that the
service conforms to.

This section how to use the package to interact with the various endpoints associated
with a STAC API service. The section is organized by the spec that each set of endpoints is associated with and also
includes user guides for working with paginated responses (from the ``/collections/{collection_id}/items`` and
``/search`` endpoints)..

API Client
+++++++++++++

The :class:`pystac_client.Client` class is the main interface for working with services that conform to the STAC API spec.
This class inherits from the :class:`pystac.Catalog` class and in addition to the methods and attributes implemented by
a Catalog, it also includes convenience methods and attributes for:

* Checking conformance to various specs
* Querying a search endpoint (if the API conforms to the STAC API - Item Search spec)

Create an Instance
__________________

The easiest way to create an :class:`~pystac_client.Client` instance is using the ``pystac_client.Client.open`` method (inherited
from :meth:`pystac.STACObject.from_file`). The following code creates an instance by making a call to the Astraea Earth
OnDemand landing page.

.. code-block:: python

    >>> from pystac_client.Client import Client
    >>> api = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1')
    >>> api.title
    'microsoft-pc'


Supported Specifications
------------------------

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
* `STAC API - Features <https://github.com/radiantearth/stac-api-spec/tree/master/ogcapi-features>`__ (based on
  `OGC API - Features <https://www.ogc.org/standards/ogcapi-features>`__)

Check Conformance
_________________

You can use the :meth:`pystac_client.Client.conforms_to` method to check conformance against conformance classes (specs)
commonly used in STAC APIs. This method provides the ability to check both against a single conformance URI (e.g.
``'https://api.stacspec.org/v1.0.0-beta.1/core'``), or against all known conformance URIs for a given spec. This allows
the package to be used with older APIs that may publish conformance URIs corresponding to older version of the spec or
that were not defined explicitly in the spec when the service was created.

To check against all conformance URIs for a given spec, use the attributes of :class:`pystac_client.ConformanceClasses`
rather than URI strings:

.. code-block:: python

    >>> from pystac_client import ConformanceClasses
    >>> api.conforms_to(ConformanceClasses.STAC_API_ITEM_SEARCH)
    True

To check against a single URI you can pass a string to the :meth:`~pystac_client.Client.conforms_to` method. This can be any
string at all, but you may want to use the :attr:`~pystac_client.conformance.ConformanceClass.uri` of the given conformance
class as these represent the official conformance URIs defined in the STAC API spec.

.. code-block:: python

    >>> api.conforms_to(ConformanceClasses.STAC_API_ITEM_SEARCH.uri)
    False
    >>> ConformanceClasses.STAC_API_ITEM_SEARCH.uri
    'https://api.stacspec.org/v1.0.0-beta.1/item-search'

Collections
+++++++++++

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

Item Search
-----------

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

* :meth:`ItemSearch.item_collections <pystac_client.ItemSearch.item_collections>`: iterates over *pages* of results,
  yielding an :class:`~pystac_client.ItemCollection` for each page of results.
* :meth:`ItemSearch.items <pystac_client.ItemSearch.items>`: iterate over individual results, yielding a
  :class:`pystac.Item` instance for all items that match the search criteria.

.. code-block:: python

    >>> for item in results.items():
    ...     print(item.id)
    S2B_OPER_MSI_L2A_TL_SGS__20190101T200120_A009518_T18TXP_N02.11
    MCD43A4.A2019010.h12v04.006.2019022234410
    MCD43A4.A2019009.h12v04.006.2019022222645
    MYD11A1.A2019002.h12v04.006.2019003174703
    MYD11A1.A2019001.h12v04.006.2019002165238

The :meth:`~pystac_client.ItemSearch.items` method handles retrieval of successive pages of results by finding any links
with a ``"rel"`` type of ``"next"`` and parsing them to construct the next request. The default implementation of this
``"next"`` link parsing assumes that the link follows the spec for an extended STAC link as described in the
`STAC API - Item Search: Paging <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#paging>`__
section. See the :mod:`Paging <pystac_client.paging>` docs for details on how to customize this behavior.
