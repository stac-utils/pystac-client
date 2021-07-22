import os
from typing import Any

import pystac
import pystac.validation

from pystac_client.conformance import ConformanceClasses, ConformanceMixin
from pystac_client.item_search import ItemSearch
from pystac_client.stac_api_io import StacApiIO


class Client(pystac.Catalog, ConformanceMixin):
    """Instances of the ``Client`` class inherit from :class:`pystac.Catalog` and provide a convenient way of interacting
    with Catalogs OR APIs that conform to the `STAC API spec <https://github.com/radiantearth/stac-api-spec>`_. In addition
    to being a valid `STAC Catalog <https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/catalog-spec.md>`_ the
    API must have a ``"conformsTo"`` property that lists the conformance URIs.

    All :class:`~pystac_client.Client` instances must be given a ``conformance`` argument at instantiation, and when calling
    the :meth:`~pystac_client.Client.from_dict` method the dictionary must contain a ``"conformsTo"`` attribute. If this is
    not true then a :exc:`KeyError` is raised.

    In addition to the methods and attributes inherited from :class:`pystac.Catalog`, this class offers some convenience
    methods to testing conformance to various specs.

    Attributes
    ----------

    conformance : List[str]
        The list of conformance URIs detailing the capabilities of the service. This object adheres to the
        `OGC API - Features conformance declaration
        <http://docs.opengeospatial.org/is/17-069r3/17-069r3.html#_declaration_of_conformance_classes>`_.
    """
    def __repr__(self):
        return '<Client id={}>'.format(self.id)

    @classmethod
    def open(cls, url=None, headers=None):
        """Alias for PySTAC's STAC Object `from_file` method

        Parameters
        ----------
        url : str, optional
            The URL of a STAC Catalog. If not specified, this will use the `STAC_URL` environment variable.

        Returns
        -------
        catalog : Client
        """

        if url is None:
            url = os.environ.get("STAC_URL")

        if url is None:
            raise TypeError(
                "'url' must be specified or the 'STAC_URL' environment variable must be set.")

        stac_io = StacApiIO(headers=headers)

        cat = cls.from_file(url, stac_io)
        return cat

    @classmethod
    def from_dict(cls, d, *args, **kwargs) -> "Client":
        """

        Raises
        ------
        pystac_client.exceptions.ConformanceError
            If the Catalog does not publish conformance URIs in either a ``"conformsTo"`` attribute in the landing page
            response or in a ``/conformance``. According to the STAC API - Core spec, services must publish this as
            part of a ``"conformsTo"`` attribute, but some legacy APIs fail to do so.
        """
        conformance = d.pop('conformsTo', None)

        cat = super().from_dict(d, *args, **kwargs)
        cat.conformance = conformance
        cat.conforms_to(ConformanceClasses.CORE)

        return cat

    def get_collections_list(self):
        """Gets list of available collections from this Catalog. Alias for get_child_links since children
            of an API are always and only ever collections
        """
        return self.get_child_links()

    def search(self, **kwargs: Any) -> ItemSearch:
        """Query the ``/search`` endpoint using the given parameters.

        This method returns an :class:`~pystac_client.ItemSearch` instance, see that class's documentation
        for details on how to get the number of matches and iterate over results. All keyword arguments are passed
        directly to the :class:`~pystac_client.ItemSearch` instance.

        .. warning::

            This method is only implemented if the API conforms to the
            `STAC API - Item Search <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__ spec
            *and* contains a link with a ``"rel"`` type of ``"search"`` in its root catalog.
            If the API does not meet either of these criteria, this method will raise a :exc:`NotImplementedError`.

        Parameters
        ----------
        **kwargs : Any pameter to the ItemSearch class, other than `url`, `conformance`, and `stac_io` which are set
        from this Client instance

        Returns
        -------
        results : ItemSearch

        Raises
        ------
        NotImplementedError
            If the API does not conform to the `Item Search spec
            <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__ or does not have a link with
            a ``"rel"`` type of ``"search"``.
        """

        search_link = self.get_single_link('search')
        if search_link is None:
            raise NotImplementedError(
                'No link with "rel" type of "search" could be found in this catalog')
        # TODO - check method in provided search link against method requested here

        return ItemSearch(search_link.target,
                          conformance=self.conformance,
                          stac_io=self._stac_io,
                          client=self,
                          **kwargs)
