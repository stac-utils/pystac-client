STAC API
========

The most basic implementation of a STAC API is simply an endpoint that returns a valid STAC Catalog. Besides being a
valid STAC Catalog, the JSON object must contain a ``"conformsTo"`` attribute that is a list of conformance URIs for
the standards that the service conforms to.

``API`` Class
-------------

The :class:`pystac_api.API` class is the main interface for working with services that conform to the STAC API spec.
This class inherits from the :class:`pystac.Catalog` class and in addition to the methods and attributes implemented by
a Catalog, it also includes the following convenience methods and attributes for checking conformance to various specs.

All :class:`~pystac_api.API` instances must be given a ``conformance`` argument at instantiation, and when calling the
:meth:`~pystac_api.API.from_dict` method the dictionary must contain a ``"conformsTo"`` attribute. If this is not true
then a :exc:`KeyError` will be raised.

Create an Instance
++++++++++++++++++

The easiest way to create an :class:`pystac_api.API` instance is using the :meth:`pystac_api.API.from_file` method. The
following code creates an instance by making a call to the Astraea Earth OnDemand landing page.

.. code-block:: python

    >>> from pystac_api.api import API
    >>> api = API.from_file('https://eod-catalog-svc-prod.astraea.earth')
    >>> api.title
    'Astraea Earth OnDemand'

Check Conformance
+++++++++++++++++

You can use the :meth:`pystac_api.API.conforms_to` method to check conformance against conformance classes (specs)
commonly used in STAC APIs. This method provides the ability to check both against a single conformance URI (e.g.
``'https://api.stacspec.org/v1.0.0-beta.1/core'``), or against all known conformance URIs for a given spec. This allows
the package to be used with older APIs that may publish conformance URIs corresponding to older version of the spec or
that were not defined explicity in the spec when the service was created.

To check against all conformance URIs for a given spec, use the attributes of :class:`pystac_api.ConformanceClasses`
rather than URI strings:

.. code-block:: python

    >>> from pystac_api import ConformanceClasses
    >>> api.conforms_to(ConformanceClasses.STAC_API_CORE)
    True

To check against a single URI you can pass a string to the :meth:`~pystac_api.API.conforms_to` method. This can be any
string at all, but you may want to use the :attr:`~pystac_api.conformance.ConformanceClass.uri` of the given conformance
class as these represent the official conformance URIs defined in the STAC API spec.

.. code-block:: python

    >>> api.conforms_to(ConformanceClasses.STAC_API_CORE.uri)
    False
    >>> ConformanceClasses.STAC_API_CORE.uri
    'https://api.stacspec.org/v1.0.0-beta.1/core'

Collections
-----------

STAC APIs may provide a curated list of catalogs and collections via their ``"links"`` attribute. Links with a ``"rel"``
type of ``"child"`` represent catalogs or collections provided by the API. Since :class:`~pystac_api.API` instances are
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
