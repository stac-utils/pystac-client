from enum import Enum
import re


class ConformanceClasses(Enum):
    """Enumeration class for Conformance Classes

    """

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
