"""This module defines a :class:`ConformanceClasses` class that can be used to check conformance to a spec based on the
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
from enum import Enum

import re


class ConformanceClasses(Enum):

    stac_prefix = re.escape("https://api.stacspec.org/v1.0.")

    # defined conformance classes regexes
    CORE = fr"{stac_prefix}(.*){re.escape('/core')}"
    ITEM_SEARCH = fr"{stac_prefix}(.*){re.escape('/item-search')}"
    CONTEXT = fr"{stac_prefix}(.*){re.escape('/item-search#context')}"
    FIELDS = fr"{stac_prefix}(.*){re.escape('/item-search#fields')}"
    SORT = fr"{stac_prefix}(.*){re.escape('/item-search#sort')}"
    QUERY = fr"{stac_prefix}(.*){re.escape('/item-search#query')}"
    FILTER = fr"{stac_prefix}(.*){re.escape('/item-search#filter')}"
    COLLECTIONS = re.escape("http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30")


CONFORMANCE_URIS = {c.name: c.value for c in ConformanceClasses}
