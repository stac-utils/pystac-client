import re
from enum import Enum


class ConformanceClasses(Enum):
    """Enumeration class for Conformance Classes"""

    stac_prefix = re.escape("https://api.stacspec.org/v1.0.")

    # defined conformance classes regexes
    CORE = rf"{stac_prefix}(.*){re.escape('/core')}"
    COLLECTIONS = rf"{stac_prefix}(.*){re.escape('/collections')}"

    # this is ogcapi-features instead of just features for historical reasons,
    # even thought this is a STAC API conformance class
    FEATURES = rf"{stac_prefix}(.*){re.escape('/ogcapi-features')}"
    ITEM_SEARCH = rf"{stac_prefix}(.*){re.escape('/item-search')}"

    CONTEXT = rf"{stac_prefix}(.*){re.escape('/item-search#context')}"
    FIELDS = rf"{stac_prefix}(.*){re.escape('/item-search#fields')}"
    SORT = rf"{stac_prefix}(.*){re.escape('/item-search#sort')}"
    QUERY = rf"{stac_prefix}(.*){re.escape('/item-search#query')}"
    FILTER = rf"{stac_prefix}(.*){re.escape('/item-search#filter')}"


CONFORMANCE_URIS = {c.name: c.value for c in ConformanceClasses}
