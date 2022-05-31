import re
from enum import Enum


class ConformanceClasses(Enum):
    """Enumeration class for Conformance Classes"""

    stac_prefix = re.escape("https://api.stacspec.org/v1.0.")

    # defined conformance classes regexes
    CORE = rf"{stac_prefix}(.*){re.escape('/core')}"
    ITEM_SEARCH = rf"{stac_prefix}(.*){re.escape('/item-search')}"
    CONTEXT = rf"{stac_prefix}(.*){re.escape('/item-search#context')}"
    FIELDS = rf"{stac_prefix}(.*){re.escape('/item-search#fields')}"
    SORT = rf"{stac_prefix}(.*){re.escape('/item-search#sort')}"
    QUERY = rf"{stac_prefix}(.*){re.escape('/item-search#query')}"
    FILTER = rf"{stac_prefix}(.*){re.escape('/item-search#filter')}"
    COLLECTIONS = re.escape(
        "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30"
    )


CONFORMANCE_URIS = {c.name: c.value for c in ConformanceClasses}
