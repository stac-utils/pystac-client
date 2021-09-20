API Reference
=============

This API reference is auto-generated for the Python docstrings,
and organized by the section of the :stac-spec:`STAC Spec <>` they relate to, if related
to a specific spec item.

pystac-client
------

.. module:: pystac-client

Client
----------

Client is the base PySTAC-Client that inherits from :class:`Catalog <pystac.Catalog>`.
In addition to the PySTAC functionality, Client allows opening of API URLs, understanding of
conformance, and support for searching and paging through results.

.. autoclass:: pystac_client.Client
   :members:
   :undoc-members:
   :show-inheritance:

Collection Client
----------

Client is the a PySTAC-Client that inherits from :class:`Collection <pystac.Collection>`.
In addition to the PySTAC functionality, CollectionClient allows opening of API URLs, and iterating
through items at a search endpoint, if supported.

.. autoclass:: pystac_client.CollectionClient
   :members:
   :undoc-members:

Item Search
----------

The `ItemSearch` class rerpesents a search of a STAC API.

.. autoclass:: pystac_client.ItemSearch
   :members:
   :undoc-members:

STAC API IO
----------------

The StacApiIO class inherits from the :class:`Collection <pystac.DefaultStacIO>` class and allows
for reading over http, such as with REST APIs.

.. autoclass:: pystac_client.StacApiIO 
   :members:
   :undoc-members:
   :show-inheritance:


Conformance
-----------

.. automodule:: pystac_client.conformance
    :members:
    :undoc-members:
    :show-inheritance:


Exceptions
----------

.. automodule:: pystac_client.exceptions
    :members:
    :undoc-members:
    :show-inheritance:
