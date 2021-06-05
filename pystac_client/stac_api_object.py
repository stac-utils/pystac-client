from typing import List, Union

from pystac_client.conformance import ConformanceClass


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
