from copy import deepcopy
from typing import Union

import pystac
import pystac.stac_object
import pystac.validation

from pystac_api.conformance import ConformanceClass, ConformanceClasses
from pystac_api.exceptions import ConformanceError


class API(pystac.Catalog):
    """Instances of the ``API`` class inherit from :class:`pystac.Catalog` and provide a convenient way of interacting
    with APIs that conform to the `STAC API spec <https://github.com/radiantearth/stac-api-spec>`_. In addition to being
    a valid `STAC Catalog <https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/catalog-spec.md>`_ the
    API must have a ``"conformsTo"`` property that lists the conformance URIs.

    In addition to the methods and attributes inherited from :class:`pystac.Catalog`, this class offers some convenience
    methods to testing conformance to various specs.

    Attributes
    ----------

    conformance : List[str]
        The list of conformance URIs detailing the capabilities of the service. This object adheres to the
        `OGC API - Features conformance declaration
        <http://docs.opengeospatial.org/is/17-069r3/17-069r3.html#_declaration_of_conformance_classes>`_.
    """

    def __init__(
            self,
            id,
            description,
            title=None,
            stac_extensions=None,
            conformance=None,
            extra_fields=None,
            href=None,
            catalog_type=None,
    ):
        super().__init__(id=id, description=description, title=title, stac_extensions=stac_extensions,
                         extra_fields=extra_fields, href=href, catalog_type=catalog_type)

        self.conformance = conformance

        # Check that the API conforms to the STAC API - Core spec
        if not self.conforms_to(ConformanceClasses.STAC_API_CORE):
            allowed_uris = "\n\t".join(ConformanceClasses.STAC_API_CORE.all_uris)
            raise ConformanceError(
                'API does not conform to {ConformanceClasses.STAC_API_CORE}. Must contain one of the following '
                f'URIs to conform (preferably the first):\n\t{allowed_uris}.'
            )

    def __repr__(self):
        return '<API id={}>'.format(self.id)

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
        pystac_api.exceptions.ConformanceError
            If the API does not publish conformance URIs in either a ``"conformsTo"`` attribute in the landing page
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
        conformance = d.pop('conformsTo')

        d.pop('stac_version')

        api = cls(
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
                api.remove_links('root')

            if link['rel'] != 'self' or href is None:
                api.add_link(pystac.Link.from_dict(link))

        return api

    def conforms_to(self, spec: Union[str, ConformanceClass]) -> bool:
        """Whether the API conforms to the given standard. This method only checks against the ``"conformsTo"``
        property from the API landing page and does not make any additional calls to a ``/conformance`` endpoint
        even if the API provides such an endpoint.

        Parameters
        ----------
        spec : str or ConformanceClass
            Either a :class:`~pystac_api.conformance.ConformanceClass` instance or the URI string for the spec.

        Examples
        --------
        >>> from pystac_api import ConformanceClasses
        >>> api.conforms_to(ConformanceClasses.STAC_API_CORE)
        True
        """
        if not self.conformance:
            return False
        for conformance_uri in self.conformance:
            if isinstance(spec, str) and conformance_uri == spec:
                return True
            if conformance_uri in spec:
                return True
        return False
