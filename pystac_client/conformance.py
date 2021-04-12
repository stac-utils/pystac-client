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
>>> 'http://stacspec.org/spec/api/1.0.0-beta.1/core' in STAC_API_CORE
True

Test that a URI is the official STAC API - Core conformance URI

>>> 'http://stacspec.org/spec/api/1.0.0-beta.1' == STAC_API_CORE
False
>>> 'http://stacspec.org/spec/api/1.0.0-beta.1' in STAC_API_CORE
True
"""
from collections.abc import Container
from typing import List, Optional, Set


class ConformanceClass(Container):
    """Class for working with the various specs that STAC APIs may conform with and testing conformance based on URIs.

    Parameters
    ----------
    name : str
        The name of the spec (e.g. "STAC API - Core").
    uri : str
        The official conformance URI for the spec. This should be the most up-to-date URI associated with this spec. To
        include legacy or alternative URIs in the conformance checks, use the ``alternative_uris`` argument.
    alternative_uris : set, optional
        A set of additional URIs that should be considered as conforming to this spec.
    """
    def __init__(self, name: str, uri: str, alternative_uris: Optional[Set[str]] = None):
        self._name = name
        self._uri = uri
        self._alternative_uris = set(alternative_uris or [])

    @property
    def name(self) -> str:
        """The human-readable name of the spec."""
        return self._name

    @property
    def all_uris(self) -> List[str]:
        """List of all URIs associated with this spec. The first URI will always be the official one
        (from the :attr:`ConformanceClass.uri` property). An API listing *any* of these URIs in its ``"conformsTo"``
        property will be treated as conforming to the spec."""
        return [self.uri] + list(self.alternative_uris)

    @property
    def uri(self) -> str:
        """The official conformance URI for this spec."""
        return str(self._uri)

    @property
    def alternative_uris(self) -> Set[str]:
        """A set of alternative URIs for this spec."""
        return set(self._alternative_uris)

    def __contains__(self, item):
        return item in self.all_uris

    def __eq__(self, other):
        uri = getattr(other, 'uri', other)
        return uri == self.uri


STAC_PREFIX = 'https://api.stacspec.org/v1.0.0-beta.1'
STAC_PREFIX_LEGACY = 'http://stacspec.org/spec/api/1.0.0-beta.1'

STAC_API_CORE = ConformanceClass(name='STAC API - Core',
                                 uri=f'{STAC_PREFIX}/core',
                                 alternative_uris={f'{STAC_PREFIX_LEGACY}/core'})
"""Used to test conformance with the `STAC API - Core spec
<https://github.com/radiantearth/stac-api-spec/tree/master/core>`__."""

STAC_API_ITEM_SEARCH = ConformanceClass(name='STAC API - Item Search',
                                        uri=f'{STAC_PREFIX}/item-search',
                                        alternative_uris={f'{STAC_PREFIX_LEGACY}/req/stac-search'})
"""Used to test conformance with the `STAC API - Item Search spec
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__."""

STAC_API_ITEM_SEARCH_CONTEXT_EXT = ConformanceClass(
    name='STAC API - Item Search: Context Extension',
    uri=f'{STAC_API_ITEM_SEARCH.uri}#context',
    alternative_uris={f'{STAC_PREFIX_LEGACY}/req/context'})
"""Used to test conformance with the `Context Extension
<https://github.com/radiantearth/stac-api-spec/tree/master/fragments/context>`__ to the STAC API - Item Search"""


class ConformanceClasses:
    """Enumerates the conformance classes used by this package."""
    STAC_API_CORE = STAC_API_CORE
    STAC_API_ITEM_SEARCH = STAC_API_ITEM_SEARCH
    STAC_API_ITEM_SEARCH_CONTEXT_EXT = STAC_API_ITEM_SEARCH_CONTEXT_EXT
