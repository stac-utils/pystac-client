from typing import List, Union

from pystac.extensions import ExtensionError

import pystac_client
from pystac_client.conformance import ConformanceClass


class APIExtensionIndex:
    """Defines methods for accessing extension functionality.

    Examples
    --------

    To access a specific extension, use the __getitem__ on this class with the
    extension ID:

    >>> from pystac_client import Client
    >>> api = Client.from_file(...)
    >>> api.api_ext.context
    <pystac_client.extensions.context.ContextAPIExtension object at 0x1035669d0>
    """
    def __init__(self, stac_object):
        self.stac_object = stac_object

    def __getitem__(self, extension_id):
        """Gets the extension object for the given extension."""
        # Check to make sure this is a registered extension.
        if not pystac_client.STAC_API_EXTENSIONS.is_registered_extension(extension_id):
            raise ExtensionError("'{}' is not an extension "
                                 "registered with pystac-client".format(extension_id))

        if not self.implements(extension_id):
            raise ExtensionError("{} does not implement the {} extension. "
                                 "Use the 'ext.enable' method to enable this extension "
                                 "first.".format(self.stac_object, extension_id))

        return pystac_client.STAC_API_EXTENSIONS.extend_object(extension_id, self.stac_object)

    def __getattr__(self, extension_id):
        """Gets an extension based on a dynamic attribute. This takes the attribute name and passes it to __getitem__.
        This allows the following two lines to be equivalent:

            item.ext["label"].label_properties
            item.ext.label.label_properties
        """
        if extension_id.startswith('__') and hasattr(APIExtensionIndex, extension_id):
            return self.__getattribute__(extension_id)
        return self[extension_id]

    def implements(self, extension_id: str):
        """Returns ``True`` if the associated object implements the given extension. Since a STAC API must also be a
        valid STAC Catalog, it may have a combination of static STAC Catalog extensions (defined in the
        "stac_extensions" property) and conformance URIs defined in the "conformsTo" property (as specified in the
        STAC API spec).

        Parameters
        ----------
        extension_id : str
            The extension ID to check. This must be an ID corresponding to one of the IDs in
            :obj:`pystac_client.API_STAC_EXTENSIONS`.

        Returns
        -------
        bool
            True if the object implements the extensions
        """
        try:
            extension_class = pystac_client.STAC_API_EXTENSIONS.get_extension_class(
                extension_id, self.stac_object.__class__)
            extension_conformance = getattr(extension_class, 'conformance', None)
            return self.stac_object.conforms_to(extension_conformance)
        except ExtensionError:
            return False


class STACAPIObjectMixin:
    """A mixin class that adds functionality for checking conformance against various STAC API specs."""

    _conformance = []

    @property
    def conformance(self) -> List[str]:
        """Overwrite in the sub-class to list the conformance URIs for this object."""
        return self._conformance

    @conformance.setter
    def conformance(self, value):
        self._conformance = value

    def conforms_to(self, spec: Union[str, ConformanceClass]) -> bool:
        """Whether the API conforms to the given standard. This method only checks against the ``"conformsTo"``
        property from the API landing page and does not make any additional calls to a ``/conformance`` endpoint
        even if the API provides such an endpoint.

        Parameters
        ----------
        spec : str or ConformanceClass
            Either a :class:`~pystac_client.conformance.ConformanceClass` instance or the URI string for the spec.

        Returns
        -------
        bool
            Indicates if the API conforms to the given spec or URI.
        """
        if not self.conformance or not spec:
            return False
        for conformance_uri in self.conformance:
            if isinstance(spec, str) and conformance_uri == spec:
                return True
            if conformance_uri in spec:
                return True
        return False

    @property
    def api_ext(self):
        return APIExtensionIndex(self)
