from copy import deepcopy
from typing import Callable, Optional
from urllib.request import Request

import pystac
import pystac.stac_object
import pystac.validation
from pystac import STAC_IO

from pystac_client.conformance import ConformanceClasses
from pystac_client.exceptions import ConformanceError
from pystac_client.item_search import (
    BBoxLike,
    CollectionsLike,
    DatetimeLike,
    IDsLike,
    IntersectsLike,
    QueryLike,
    ItemSearch,
)
from pystac_client.stac_api_object import STACAPIObjectMixin


class Client(pystac.Catalog, STACAPIObjectMixin):
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
    def __init__(self,
                 id,
                 description,
                 title=None,
                 stac_extensions=None,
                 extra_fields=None,
                 href=None,
                 catalog_type=None,
                 conformance=None,
                 headers=None):
        super().__init__(id=id,
                         description=description,
                         title=title,
                         stac_extensions=stac_extensions,
                         extra_fields=extra_fields,
                         href=href,
                         catalog_type=catalog_type)

        self.conformance = conformance

        # Check that the API conforms to the STAC API - Core spec (or ignore if None)
        if conformance is not None and not self.conforms_to(ConformanceClasses.STAC_API_CORE):
            allowed_uris = "\n\t".join(ConformanceClasses.STAC_API_CORE.all_uris)
            raise ConformanceError(
                'API does not conform to {ConformanceClasses.STAC_API_CORE}. Must contain one of the following '
                f'URIs to conform (preferably the first):\n\t{allowed_uris}.')

        self.headers = headers or {}

    def __repr__(self):
        return '<Catalog id={}>'.format(self.id)

    @classmethod
    def open(cls, url, headers=None):
        """Alias for PySTAC's STAC Object `from_file` method

        Parameters
        ----------
        url : str
            The URL of a STAC Catalog

        Returns
        -------
        catalog : Client
        """
        import pystac_client.stac_io

        def read_text_method(url):
            request = Request(url, headers=headers or {})
            return pystac_client.stac_io.read_text_method(request)

        old_read_text_method = STAC_IO.read_text_method
        STAC_IO.read_text_method = read_text_method
        catalog = cls.from_file(url)
        STAC_IO.read_text_method = old_read_text_method
        catalog.headers = headers
        return catalog

    @classmethod
    def from_dict(
        cls,
        d,
        href=None,
        root=None,
    ):
        """Overwrites the :meth:`pystac.Catalog.from_dict` method to add the ``user_agent`` initialization argument
        and to check if the content conforms to the STAC API - Core spec.

        Raises
        ------
        pystac_client.exceptions.ConformanceError
            If the Catalog does not publish conformance URIs in either a ``"conformsTo"`` attribute in the landing page
            response or in a ``/conformance``. According to the STAC API - Core spec, services must publish this as
            part of a ``"conformsTo"`` attribute, but some legacy APIs fail to do so.
        """
        catalog_type = pystac.CatalogType.determine_type(d)

        d = deepcopy(d)

        id = d.pop('id')
        description = d.pop('description')
        title = d.pop('title', None)
        stac_extensions = d.pop('stac_extensions', None)
        links = d.pop('links')
        # allow for no conformance, for now
        conformance = d.pop('conformsTo', None)

        d.pop('stac_version')

        catalog = cls(
            id=id,
            description=description,
            title=title,
            stac_extensions=stac_extensions,
            conformance=conformance,
            extra_fields=d,
            href=href,
            catalog_type=catalog_type,
        )

        for link in links:
            if link['rel'] == 'root':
                # Remove the link that's generated in Catalog's constructor.
                catalog.remove_links('root')

            if link['rel'] != 'self' or href is None:
                catalog.add_link(pystac.Link.from_dict(link))

        return catalog

    @classmethod
    def get_collections_list(self):
        """Gets list of available collections from this Catalog. Alias for get_child_links since children
            of an API are always and only ever collections
        """
        return self.get_child_links()

    def search(self,
               *,
               limit: Optional[int] = None,
               bbox: Optional[BBoxLike] = None,
               datetime: Optional[DatetimeLike] = None,
               intersects: Optional[IntersectsLike] = None,
               ids: Optional[IDsLike] = None,
               collections: Optional[CollectionsLike] = None,
               query: Optional[QueryLike] = None,
               max_items: Optional[int] = None,
               method: Optional[str] = 'POST',
               next_resolver: Optional[Callable] = None) -> ItemSearch:
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
        limit : int, optional
            The maximum number of items to return *per page*. Defaults to ``None``, which falls back to the limit set
            by the service.
        bbox: list or tuple or Iterator or str, optional
            May be a list, tuple, or iterator representing a bounding box of 2D or 3D coordinates. Results will be
            filtered to only those intersecting the bounding box.
        datetime: str or datetime.datetime or list or tuple or Iterator, optional
            Either a single datetime or datetime range used to filter results. You may express a single datetime using a
            :class:`datetime.datetime` instance, a `RFC 3339-compliant <https://tools.ietf.org/html/rfc3339>`__ timestamp,
            or a simple date string (see below). Instances of :class:`datetime.datetime` may be either timezone aware or
            unaware. Timezone aware instances will be converted to a UTC timestamp before being passed to the endpoint.
            Timezone unaware instances are assumed to represent UTC timestamps. You may represent a datetime range using a
            ``"/"`` separated string as described in the spec, or a list, tuple, or iterator of 2 timestamps or datetime
            instances. For open-ended ranges, use either ``".."`` (``'2020-01-01:00:00:00Z/..'``,
            ``['2020-01-01:00:00:00Z', '..']``) or a value of ``None`` (``['2020-01-01:00:00:00Z', None]``).

            If using a simple date string, the datetime can be specified in ``YYYY-mm-dd`` format, optionally truncating
            to ``YYYY-mm`` or just ``YYYY``. Simple date strings will be expanded to include the entire time period, for
            example:

            - ``2017`` expands to ``2017-01-01T00:00:00Z/2017-12-31T23:59:59Z``
            - ``2017-06`` expands to ``2017-06-01T00:00:00Z/2017-06-30T23:59:59Z``
            - ``2017-06-10`` expands to ``2017-06-10T00:00:00Z/2017-06-10T23:59:59Z``

            If used in a range, the end of the range expands to the end of that day/month/year, for example:

            - ``2017/2018`` expands to ``2017-01-01T00:00:00Z/2018-12-31T23:59:59Z``
            - ``2017-06/2017-07`` expands to ``2017-06-01T00:00:00Z/2017-07-31T23:59:59Z``
            - ``2017-06-10/2017-06-11`` expands to ``2017-06-10T00:00:00Z/2017-06-11T23:59:59Z``
        intersects: str or dict, optional
            A GeoJSON-like dictionary or JSON string. Results will be filtered to only those intersecting the geometry
        ids: list, optional
            List of Item ids to return. All other filter parameters that further restrict the number of search results
            (except ``limit``) are ignored.
        collections: list, optional
            List of one or more Collection IDs or :class:`pystac.Collection` instances. Only Items in one of the
            provided Collections will be searched
        max_items : int or None, optional
            The maximum number of items to return from the search. *Note that this is not a STAC API - Item Search
            parameter and is instead used by the client to limit the total number of returned items*.
        method : str or None, optional
            The HTTP method to use when making a request to the service. This must be either ``"GET"``, ``"POST"``, or
            ``None``. If ``None``, this will default to ``"POST"`` if the ``intersects`` argument is present and
            ``"GET"`` if not. If a ``"POST"`` request receives a ``405`` status for the response, it will automatically
            retry with a ``"GET"`` request for all subsequent requests.
        next_resolver: Callable, optional
            A callable that will be used to construct the next request based on a "next" link and the previous request.
            Defaults to using the :func:`~pystac_client.paging.simple_stac_resolver`.

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
        if self.conformance is not None and not self.conforms_to(
                ConformanceClasses.STAC_API_ITEM_SEARCH):
            spec_name = ConformanceClasses.STAC_API_ITEM_SEARCH.name
            spec_uris = '\n\t'.join(ConformanceClasses.STAC_API_ITEM_SEARCH.all_uris)
            msg = f'This service does not conform to the {spec_name} spec and therefore the search method is not ' \
                  f'implemented. Services must publish one of the following conformance URIs in order to conform to ' \
                  f'this spec (preferably the first one):\n\t{spec_uris}'
            raise NotImplementedError(msg)

        search_link = self.get_single_link('search')
        if search_link is None:
            raise NotImplementedError(
                'No link with a "rel" type of "search" could be found in this services\'s '
                'root catalog.')

        return ItemSearch(search_link.target,
                          limit=limit,
                          bbox=bbox,
                          datetime=datetime,
                          intersects=intersects,
                          ids=ids,
                          collections=collections,
                          query=query,
                          max_items=max_items,
                          method=method,
                          headers=self.headers,
                          conformance=self.conformance,
                          next_resolver=next_resolver)
