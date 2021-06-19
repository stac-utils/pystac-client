"""This module defines a :class:`ConformanceClass` class that can be used to check conformance to a spec based on the
presence of a conformance URI. Each instance has a single :attr:`ConformanceClass.uri` property that represents the
most up-to-date official conformance URI for that spec. Because the STAC API spec has been rapidly evolving, many APIs
publish other conformance URIs that were defined in previous iterations of the spec, or are defined by other entities.
These unofficial URIs are captured in the :attr:`ConformanceClass.alternative_uris` property.

To check that a given conformance URI conforms to any of the URIs (official or unofficial) for a given spec, use an
``in`` comparison. For a strict check that the URI is the same as the *official* URI for this spec, use ``==``.

This module also provides :class:`ConformanceClass` instances for the following specs:

* :obj:`STAC_API_CORE`

Examples
--------

Test that a URI conforms to any version of the STAC API - Core spec

>>> from pystac_client.conformance import STAC_API_CORE
>>> 'http://stacspec.org/spec/api/1.0.0-beta.2/core' in STAC_API_CORE
True

Test that a URI is the official STAC API - Core conformance URI

>>> 'http://stacspec.org/spec/api/1.0.0-beta.2' == STAC_API_CORE
False
>>> 'http://stacspec.org/spec/api/1.0.0-beta.2' in STAC_API_CORE
True
"""
from typing import List, Optional

STAC_PREFIXES = ['https://api.stacspec.org/v1.0.0-beta.2', 'https://api.stacspec.org/v1.0.0-beta.1']

CONFORMANCE_CLASSES = {
    "core": {
        "name": "STAC API - Core",
        "uris": [f"{p}/core" for p in STAC_PREFIXES]
    },
    "item-search": {
        "name": "STAC API - Item Search",
        "uris": [f"{p}/item-search" for p in STAC_PREFIXES]
    },
    "item-search#context": {
        "name": "STAC API - Item Search: Context Extension",
        "uris": [f"{p}/item-search#context" for p in STAC_PREFIXES]
    },
    "item-search#fields": {
        "name": "STAC API - Item Search: Fields Extension",
        "uris": [f"{p}/item-search#fields" for p in STAC_PREFIXES]
    },
    "item-search#sort": {
        "name": "STAC API - Item Search: Sort Extension",
        "uris": [f"{p}/item-search#sort" for p in STAC_PREFIXES]
    },
    "item-search#query": {
        "name": "STAC API - Item Search: Query Extension",
        "uris": [f"{p}/item-search#query" for p in STAC_PREFIXES]
    },
    "item-search#filter": {
        "name": "STAC API - Item Search: Filter Extension",
        "uris": [f"{p}/item-search#filter" for p in STAC_PREFIXES]
    },
}


class ConformanceMixin:
    """A mixin class that adds functionality for checking conformance against various STAC API specs."""

    _conformance = []

    @property
    def conformance(self) -> Optional[List[str]]:
        return self._conformance

    @conformance.setter
    def conformance(self, value):
        self._conformance = value

    def conforms_to(self, key: str) -> bool:
        """Whether the API conforms to the given standard. This method only checks against the ``"conformsTo"``
        property from the API landing page and does not make any additional calls to a ``/conformance`` endpoint
        even if the API provides such an endpoint.

        Parameters
        ----------
        key : str
            The ``ConformanceClasses`` key to check conformance against.

        Returns
        -------
        bool
            Indicates if the API conforms to the given spec or URI.
        """

        # Conformance of None means ignore all conformance as opposed to an
        #  empty array which would indicate the API conforms to nothing
        if self.conformance is None:
            return True

        conformance_class = CONFORMANCE_CLASSES[key]

        if not any(uri in conformance_class["uris"] for uri in self.conformance):
            raise NotImplementedError(f"{conformance_class['name']} not supported")

        return True
