Usage
#####

PySTAC-Client (pystac-client) builds upon
`PySTAC <https://github.com/stac-utils/pystac>`_ library to add support
for STAC APIs in addition to static STAC catalogs. PySTAC-Client can be used with static
or dynamic (i.e., API) catalogs. Currently, pystac-client does not offer much in the way
of additional functionality if using with static catalogs, as the additional features
are for support STAC API endpoints such as `search`. However, in the future it is
expected that pystac-client will offer additional convenience functions that may be
useful for static and dynamic catalogs alike.

The most basic implementation of a STAC API is an endpoint that returns a valid STAC
Catalog, but also contains a ``"conformsTo"`` attribute that is a list of conformance
URIs for the standards that the API supports.

This section is organized by the classes that are used, which mirror parent classes
from PySTAC:

+------------------+------------+
| pystac-client    | pystac     |
+==================+============+
| Client           | Catalog    |
+------------------+------------+
| CollectionClient | Collection |
+------------------+------------+

The classes offer all of the same functions for accessing and traversing Catalogs as
in PySTAC. The documentation for pystac-client only includes new functions, it does
not duplicate documentation for inherited functions.

Client
++++++

The :class:`pystac_client.Client` class is the main interface for working with services
that conform to the STAC API spec. This class inherits from the :class:`pystac.Catalog`
class and in addition to the methods and attributes implemented by a Catalog, it also
includes convenience methods and attributes for:

* Checking conformance to various specs
* Querying a search endpoint (if the API conforms to the STAC API - Item Search spec)
* Getting jsonschema of queryables from `/queryables` endpoint (if the API conforms
  to the STAC API - Filter spec)

The preferred way to interact with any STAC Catalog or API is to create an
:class:`pystac_client.Client` instance with the ``pystac_client.Client.open`` method
on a root Catalog. This calls the :meth:`pystac.STACObject.from_file` except it
properly configures conformance and IO for reading from remote servers.

The following code creates an instance by making a call to the Microsoft Planetary
Computer root catalog.

.. code-block:: python

    >>> from pystac_client import Client
    >>> catalog = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1')
    >>> catalog.title
    'Microsoft Planetary Computer STAC API'

Some functions, such as ``Client.search`` will throw an error if the provided
Catalog/API does not support the required Conformance Class. In other cases,
such as ``Client.get_collections``, API endpoints will be used if the API
conforms, otherwise it will fall back to default behavior provided by
:class:`pystac.Catalog`.

When a ``Client`` does not conform to a particular Conformance Class, an informative
warning is raised. Similarly when falling back to the :class:`pystac.Catalog`
implementation a warning is raised. You can control the behavior of these warnings
using the standard :py:mod:`warnings` or special context managers :func:`pystac_client.warnings.strict` and
from :func:`pystac_client.warnings.ignore`.

API Conformance
---------------

This library is intended to work with any STAC static catalog or STAC API. A static
catalog will be usable more or less the same as with PySTAC, except that pystac-client
supports providing custom headers to API endpoints. (e.g., authenticating
to an API with a token).

A STAC API is a STAC Catalog that is required to advertise its capabilities in a
`conformsTo` field and implements the `STAC API - Core` spec along with other
optional specifications:

* `CORE <https://github.com/radiantearth/stac-api-spec/tree/master/core>`__
* `ITEM_SEARCH <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__
   * `FIELDS <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/fields>`__
   * `QUERY <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/query>`__
   * `SORT <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/sort>`__
   * `CONTEXT <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context>`__
   * `FILTER <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/filter>`__
* `COLLECTIONS <https://github.com/radiantearth/stac-api-spec/tree/master/collections>`__ (based on
  the `Features Collection section of OGC APO -  Features <http://docs.opengeospatial.org/is/17-069r3/17-069r3.html#_collections_>__`)
* `FEATURES <https://github.com/radiantearth/stac-api-spec/tree/master/ogcapi-features>`__ (based on
  `OGC API - Features <https://www.ogc.org/standards/ogcapi-features>`__)

The :meth:`pystac_client.Client.conforms_to` method is used to check conformance
against conformance classes (specs). To check an API for support for a given spec,
pass the `conforms_to` function the name of a :class:`ConformanceClasses`.

.. code-block:: python

    >>> catalog.conforms_to("ITEM_SEARCH")
    True

If the API does not advertise conformance with a particular spec, but it does support
it you can update `conforms_to` on the client object. For instance in `v0` of earth-search
there are no ``"conformsTo"`` uris set at all. But they can be explicitly set:

.. code-block:: python

    >>> catalog = Client.open("https://earth-search.aws.element84.com/v0")
    <stdin>:1: NoConformsTo: Server does not advertise any conformance classes.
    >>> catalog.conforms_to("ITEM_SEARCH")
    False
    >>> catalog.add_conforms_to("ITEM_SEARCH")

Note, updating ``"conformsTo"`` does not change what the server supports, it just
changes PySTAC client's understanding of what the server supports.

Configuring retry behavior
--------------------------

By default, **pystac-client** will retry requests that fail DNS lookup or have timeouts.
If you'd like to configure this behavior, e.g. to retry on some ``50x`` responses, you can configure the StacApiIO's session:

.. code-block:: python

    from requests.adapters import HTTPAdapter
    from urllib3 import Retry

    from pystac_client import Client
    from pystac_client.stac_api_io import StacApiIO

    retry = Retry(
        total=5, backoff_factor=1, status_forcelist=[502, 503, 504], allowed_methods=None
    )
    stac_api_io = StacApiIO(max_retries=retry)
    client = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1", stac_io=stac_api_io
    )

Automatically modifying results
-------------------------------

Some systems, like the `Microsoft Planetary Computer <http://planetarycomputer.microsoft.com/>`__,
have public STAC metadata but require some `authentication <https://planetarycomputer.microsoft.com/docs/concepts/sas/>`__
to access the actual assets.

``pystac-client`` provides a ``modifier`` keyword that can automatically
modify the STAC objects returned by the STAC API.

.. code-block:: python

   >>> from pystac_client import Client
   >>> import planetary_computer, requests
   >>> catalog = Client.open(
   ...    'https://planetarycomputer.microsoft.com/api/stac/v1',
   ...    modifier=planetary_computer.sign_inplace,
   ... )
   >>> item = next(catalog.get_collection("sentinel-2-l2a").get_all_items())
   >>> requests.head(item.assets["B02"].href).status_code
   200

Without the modifier, we would have received a 404 error because the asset
is in a private storage container.

``pystac-client`` expects that the ``modifier`` callable modifies the result
object in-place and returns no result. A warning is emitted if your
``modifier`` returns a non-None result that is not the same object as the
input.

Here's an example of creating your own modifier.
Because :py:class:`~pystac_client.Modifiable` is a union, the modifier function must handle a few different types of input objects, and care must be taken to ensure that you are modifying the input object (rather than a copy).
Simplifying this interface is a space for future improvement.

.. code-block:: python

    import urllib.parse

    import pystac

    from pystac_client import Client, Modifiable


    def modifier(modifiable: Modifiable) -> None:
        if isinstance(modifiable, dict):
            if modifiable["type"] == "FeatureCollection":
                new_features = list()
                for item_dict in modifiable["features"]:
                    modifier(item_dict)
                    new_features.append(item_dict)
                modifiable["features"] = new_features
            else:
                stac_object = pystac.read_dict(modifiable)
                modifier(stac_object)
                modifiable.update(stac_object.to_dict())
        else:
            for key, asset in modifiable.assets.items():
                url = urllib.parse.urlparse(asset.href)
                if not url.query:
                    asset.href = urllib.parse.urlunparse(url._replace(query="foo=bar"))
                    modifiable.assets[key] = asset


    client = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1", modifier=modifier
    )
    item_search = client.search(collections=["landsat-c2-l2"], max_items=1)
    item = next(item_search.items())
    asset = item.assets["red"]
    assert urllib.parse.urlparse(asset.href).query == "foo=bar"


Using custom certificates
-------------------------

If you need to use custom certificates in your ``pystac-client`` requests, you can
customize the :class:`StacApiIO<pystac_client.stac_api_io.StacApiIO>` instance before
creating your :class:`Client<pystac_client.Client>`.

.. code-block:: python

    >>> from pystac_client.stac_api_io import StacApiIO
    >>> from pystac_client.client import Client
    >>> stac_api_io = StacApiIO()
    >>> stac_api_io.session.verify = "/path/to/certfile"
    >>> client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", stac_io=stac_api_io)

CollectionClient
++++++++++++++++

STAC APIs may optionally implement a ``/collections`` endpoint as describe in the
`STAC API - Collections spec
<https://github.com/radiantearth/stac-api-spec/tree/master/collections>`__. This endpoint
allows clients to search or inspect items within a particular collection.

.. code-block:: python

    >>> catalog = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1')
    >>> collection = catalog.get_collection("sentinel-2-l2a")
    >>> collection.title
    'Sentinel-2 Level-2A'

:class:`pystac_client.CollectionClient` overrides :meth:`pystac.Collection.get_items`.
PySTAC will get items by iterating through all children until it gets to an ``item`` link.
PySTAC client will use the API endpoint instead: `/collections/<collection_id>/items`
(as long as `STAC API - Item Search spec
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__ is supported).

.. code-block:: python

    >>> item = next(collection.get_items(), None)

Note that calling list on this iterator will take a really long time since it will be retrieving
every itme for the whole ``"sentinel-2-l2a"`` collection.

ItemSearch
++++++++++

STAC API services may optionally implement a ``/search`` endpoint as describe in the
`STAC API - Item Search spec
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__. This
endpoint allows clients to query STAC Items across the entire service using a variety
of filter parameters. See the `Query Parameter Table
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__
from that spec for details on the meaning of each parameter.

The :meth:`pystac_client.Client.search` method provides an interface for making
requests to a service's "search" endpoint. This method returns a
:class:`pystac_client.ItemSearch` instance.

.. code-block:: python

    >>> from pystac_client import Client
    >>> catalog = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1')
    >>> results = catalog.search(
    ...     max_items=5
    ...     bbox=[-73.21, 43.99, -73.12, 44.05],
    ...     datetime=['2019-01-01T00:00:00Z', '2019-01-02T00:00:00Z'],
    ... )

Instances of :class:`~pystac_client.ItemSearch` have a handful of methods for
getting matching items into Python objects. The right method to use depends on
how many of the matches you want to consume (a single item at a time, a
page at a time, or everything) and whether you want plain Python dictionaries
representing the items, or proper ``pystac`` objects.

The following table shows the :class:`~pystac_client.ItemSearch` methods for fetching
matches, according to which set of matches to return and whether to return them as
``pystac`` objects or plain dictionaries.

================= ================================================= =========================================================
Matches to return PySTAC objects                                    Plain dictionaries
================= ================================================= =========================================================
**Single items**  :meth:`~pystac_client.ItemSearch.items`           :meth:`~pystac_client.ItemSearch.items_as_dicts`
**Pages**         :meth:`~pystac_client.ItemSearch.pages`           :meth:`~pystac_client.ItemSearch.pages_as_dicts`
**Everything**    :meth:`~pystac_client.ItemSearch.item_collection` :meth:`~pystac_client.ItemSearch.item_collection_as_dict`
================= ================================================= =========================================================

Additionally, the ``matched`` method can be used to access result metadata about
how many total items matched the query:

* :meth:`ItemSearch.matched <pystac_client.ItemSearch.matched>`: returns the number
  of hits (items) for this search if the API supports the STAC API Context Extension.
  Not all APIs support returning a total count, in which case a warning will be issued.

.. code-block:: python

    >>> for item in results.items():
    ...     print(item.id)
    S2B_OPER_MSI_L2A_TL_SGS__20190101T200120_A009518_T18TXP_N02.11
    MCD43A4.A2019010.h12v04.006.2019022234410
    MCD43A4.A2019009.h12v04.006.2019022222645
    MYD11A1.A2019002.h12v04.006.2019003174703
    MYD11A1.A2019001.h12v04.006.2019002165238

The :meth:`~pystac_client.ItemSearch.items` and related methods handle retrieval of
successive pages of results
by finding links with a ``"rel"`` type of ``"next"`` and parsing them to construct the
next request. The default
implementation of this ``"next"`` link parsing assumes that the link follows the spec for
an extended STAC link as
described in the
`STAC API - Item Search: Paging <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#paging>`__
section. See the :mod:`Paging <pystac_client.paging>` docs for details on how to
customize this behavior.

Alternatively, the Items can be returned within ItemCollections, where each
ItemCollection is one page of results retrieved from search:

.. code-block:: python

    >>> for ic in results.pages():
    ...     for item in ic.items:
    ...         print(item.id)
    S2B_OPER_MSI_L2A_TL_SGS__20190101T200120_A009518_T18TXP_N02.11
    MCD43A4.A2019010.h12v04.006.2019022234410
    MCD43A4.A2019009.h12v04.006.2019022222645
    MYD11A1.A2019002.h12v04.006.2019003174703
    MYD11A1.A2019001.h12v04.006.2019002165238

If you do not need the :class:`pystac.Item` instances, you can instead use
:meth:`ItemSearch.items_as_dicts <pystac_client.ItemSearch.items_as_dicts>`
to retrieve dictionary representation of the items, without incurring the cost of
creating the Item objects.

.. code-block:: python

    >>> for item_dict in results.items_as_dicts():
    ...     print(item_dict["id"])
    S2B_OPER_MSI_L2A_TL_SGS__20190101T200120_A009518_T18TXP_N02.11
    MCD43A4.A2019010.h12v04.006.2019022234410
    MCD43A4.A2019009.h12v04.006.2019022222645
    MYD11A1.A2019002.h12v04.006.2019003174703
    MYD11A1.A2019001.h12v04.006.2019002165238

Query Extension
---------------

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

Sort Extension
---------------

If the Catalog supports the `Sort
extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/sort>`__,
the search request can specify the order in which the results should be sorted with
the ``sortby`` parameter.  The ``sortby`` parameter can either be a string
(e.g., ``"-properties.datetime,+id,collection"``), a list of strings
(e.g., ``["-properties.datetime", "+id", "+collection"]``), or a dictionary representing
the POST JSON format of sortby. In the string and list formats, a ``-`` prefix means a
descending sort and a ``+`` prefix or no prefix means an ascending sort.

.. code-block:: python

    >>> from pystac_client import Client
    >>> results = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1').search(
    ...     sortby="properties.datetime"
    ... )
    >>> results = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1').search(
    ...     sortby="-properties.datetime,+id,+collection"
    ... )
    >>> results = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1').search(
    ...     sortby=["-properties.datetime", "+id" , "+collection" ]
    ... )
    >>> results = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1').search(
    ...     sortby=[
                {"direction": "desc", "field": "properties.datetime"},
                {"direction": "asc", "field": "id"},
                {"direction": "asc", "field": "collection"},
            ]
    ... )

Loading data
++++++++++++

Once you've fetched your STAC :class:`Items<pystac.Item>` with ``pystac-client``, you
now can work with the data referenced by your :class:`Assets<pystac.Asset>`.  This is
out of scope for ``pystac-client``, but there's a wide variety of tools and options
available, and the correct choices depend on your type of data, your environment, and
the type of analysis you're doing.

For simple workflows, it can be easiest to load data directly using `rasterio
<https://rasterio.readthedocs.io>`_, `fiona <https://fiona.readthedocs.io/>`_, and
similar tools. Here is a simple example using **rasterio** to display data from a raster
file.

.. code-block:: python

    >>> import rasterio.plot.show
    >>> with rasterio.open(item.assets["data"].href) as dataset:
    ...     rasterio.plot.show(dataset)

For larger sets of data and more complex workflows, a common tool for working with a
large number of raster files is `xarray <https://docs.xarray.dev>`_, which provides data
structures for labelled multi-dimensional arrays. `stackstac
<https://stackstac.readthedocs.io>`_ and `odc-stac <https://odc-stac.readthedocs.io>`_
are two similar tools that can load asset data from :class:`Items<pystac.Item>` or an
:class:`ItemCollection<pystac.ItemCollection>` into an **xarray**. Here's a simple
example from **odc-stac**'s documentation:

.. code-block:: python

    >>> catalog = pystac_client.Client.open(...)
    >>> query = catalog.search(...)
    >>> xx = odc.stac.load(
    ...     query.get_items(),
    ...     bands=["red", "green", "blue"],
    ...     resolution=100,
    ... )
    >>> xx.red.plot.imshow(col="time")


See each packages's respective documentation for more examples and tutorials.
