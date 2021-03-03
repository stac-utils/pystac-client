Item Search
-----------

STAC API services may optionally implement a ``/search`` endpoint as describe in the  `STAC API - Item Search spec
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__. This endpoint allows clients to query
STAC Items across the entire service using a variety of filter parameters. See the `Query Parameter Table
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__ from that spec for
details on the meaning of each parameter.

The :meth:`pystac_api.API.search` method provides an interface for making requests to a service's
"search" endpoint. This method returns a :class:`pystac_api.item_search.ItemSearch` instance.

.. code-block:: python

    >>> from pystac_api import API
    >>> api = API.from_file('https://eod-catalog-svc-prod.astraea.earth')
    >>> results = api.search(
    ...     bbox=[-73.21, 43.99, -73.12, 44.05],
    ...     datetime=['2019-01-01T00:00:00Z', '2019-01-02T00:00:00Z'],
    ...     max_items=5
    ... )

Instances of :class:`~pystac_api.item_search.ItemSearch` are iterable, yielding :class:`pystac.Items` instances for all
items that match the search criteria.

.. code-block:: python

    >>> for item in results:
    ...     print(item.id)
    S2B_OPER_MSI_L2A_TL_SGS__20190101T200120_A009518_T18TXP_N02.11
    MCD43A4.A2019010.h12v04.006.2019022234410
    MCD43A4.A2019009.h12v04.006.2019022222645
    MYD11A1.A2019002.h12v04.006.2019003174703
    MYD11A1.A2019001.h12v04.006.2019002165238

The instances handles retrieval of successive pages of results by finding any links with a ``"rel"`` type of ``"next"``
and parsing them to construct the next request. The default implementation of this ``"next"`` link parsing assumes that
the link follows the spec for an extended STAC link as described in the `STAC API - Item Search: Paging
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search#paging>`__ section. See the
:mod:`Paging <pystac_api.paging>` docs for details on how to customize this behavior.