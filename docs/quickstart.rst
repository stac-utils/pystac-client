Quickstart
----------

PySTAC Client can be used as either a Command Line Interface (CLI) or a
Python library.

CLI
~~~

Use the CLI to quickly perform Item or Collection searches and
output or save the results.

The ``--matched`` switch performs a search with limit=1 so does not get
any Items, but gets the total number of matches which will be output to
the screen (if supported by the STAC API).

.. code-block:: console

    $ stac-client search https://earth-search.aws.element84.com/v1 -c sentinel-2-l2a --bbox -72.5 40.5 -72 41 --matched
    3141 items matched

The ``--matched`` flag can also be used for collection search to get
the total number of collections that match your search terms.


.. code-block:: console

    $ stac-client collections https://emc.spacebel.be --q sentinel-2 --matched
    76 collections matched

If the same URL is to be used over and over, define an environment
variable to be used in the CLI call:

.. code-block:: console

    $ export STAC_API_URL=https://earth-search.aws.element84.com/v1
    $ stac-client search ${STAC_API_URL} -c sentinel-2-l2a --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 --matched
    48 items matched

Without the ``--matched`` switch, all items will be fetched, paginating
if necessary. If the ``--max-items`` switch is provided it will stop
paging once that many items has been retrieved. It then prints all items
to stdout as an ItemCollection. This can be useful to pipe output to
another process such as
`stac-terminal <https://github.com/stac-utils/stac-terminal>`__,
`geojsonio-cli <https://github.com/mapbox/geojsonio-cli>`__, or
`jq <https://stedolan.github.io/jq/>`__.

.. code-block:: console

    $ stac-client search ${STAC_API_URL} -c sentinel-2-l2a --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 | stacterm cal --label platform

.. figure:: images/stacterm-cal.png
   :alt:

If the ``--save`` switch is provided instead, the results will not be
output to stdout, but instead will be saved to the specified file.

.. code-block:: console

    $ stac-client search ${STAC_API_URL} -c sentinel-2-l2a --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 --save items.json

If the Catalog supports the `Query
extension <https://github.com/radiantearth/stac-api-spec/tree/master/fragments/query>`__,
any Item property can also be included in the search. Rather than
requiring the JSON syntax the Query extension uses, pystac-client uses a
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
    created=2021-01-06
    view:sun_elevation<20

Any number of properties can be included, and each can be included more
than once to use additional operators.

.. code-block:: console

    $ stac-client search ${STAC_API_URL} -c sentinel-2-l2a --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 ---query "eo:cloud_cover<10" --matched
    10 items matched

.. code-block:: console

    $ stac-client search ${STAC_API_URL} -c sentinel-2-l2a --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 --query "eo:cloud_cover<10" "eo:cloud_cover>5" --matched
    4 items matched


Collection searches can also use multiple filters like this example
search for collections that include the term ``"biomass"`` and have
a spatial extent that intersects Scandinavia.

.. code-block:: console

    $ stac-client collections https://emc.spacebel.be --q biomass --bbox 0.09 54.72 33.31 71.36  --matched
    43 items matched

Since most STAC APIs have not yet implemented the `collection search 
extension <https://github.com/stac-api-extensions/collection-search>`__, 
``pystac-client`` will perform a limited client-side 
filter on the full list of collections using only the ``bbox``, 
``datetime``, and ``q`` (free-text search) parameters.
In the case that the STAC API does not support collection search, a
warning will be displayed to inform you that the filter is being
applied client-side.


Python
~~~~~~

First, create a Client instance configured to use a specific STAC API by the root URL of that API. For this example, we
will use `Earth Search <https://earth-search.aws.element84.com/v1>`__.

.. code-block:: python

    from pystac_client import Client

    client = Client.open("https://earth-search.aws.element84.com/v1")

Create an Item Search instance that represents a search to run. This does not actually run a search yet --
that does not happen until a method is called that requires data from the STAC API.

.. code-block:: python

    search = client.search(
        max_items=10,
        collections=["sentinel-2-c1-l2a"],
        bbox=[-72.5,40.5,-72,41]
    )

Calling ``matched()`` will send a request to the STAC API and retrieve a single item and metadata about how many Items
match the search criteria.

.. code-block:: python

    print(f"{search.matched()} items found")

The ``items()`` iterator method can be used to iterate through all resulting items. This iterator
hides the pagination behavior that the may occur if there are sufficient results. Be careful with this
method -- you could end up iterating over the entire catalog if ``max_items`` is not set!

.. code-block:: python

    for item in search.items():
        print(item.id)

Use ``item_collection()`` to convert all Items from a search into a single `PySTAC
ItemCollection <https://pystac.readthedocs.io/en/latest/api/pystac.html#pystac.ItemCollection>`__.
The ``ItemCollection`` can then be saved as a GeoJSON FeatureCollection. This requires retrieving all
of the results from the search, so it may take some time to retrieve all the paginated responses.

.. code-block:: python

    item_collection = search.item_collection()
    item_collection.save_object("my_itemcollection.json")

Some STAC APIs also implement the Collection Search Extension. Earth Search does not, so we use the
ORNL_CLOUD CMR-STAC Catalog instead:

.. code-block:: python

    client = Client.open("https://cmr.earthdata.nasa.gov/stac/ORNL_CLOUD")
    collection_search = client.collection_search(
        q="rain",
    )
    print(f"{collection_search.matched()} collections found")


The ``collections()`` iterator method can be used to iterate through all
resulting collections.

.. code-block:: python

    for collection in collection_search.collections():
        print(collection.id)

