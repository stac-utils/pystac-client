from __future__ import annotations

import re
from enum import Enum


class ConformanceClasses(Enum):
    """Enumeration class for Conformance Classes"""

    stac_prefix = "https://api.stacspec.org/v1.0."

    # defined conformance classes regexes
    CORE = "/core"
    COLLECTIONS = "/collections"

    # this is ogcapi-features instead of just features for historical reasons,
    # even thought this is a STAC API conformance class
    FEATURES = "/ogcapi-features"
    ITEM_SEARCH = "/item-search"

    CONTEXT = "/item-search#context"
    FIELDS = "/item-search#fields"
    SORT = "/item-search#sort"
    QUERY = "/item-search#query"
    FILTER = "/item-search#filter"

    @classmethod
    def valid_uri(cls, endpoint: str) -> str:
        return f"{cls.stac_prefix.value}*{endpoint}"

    @classmethod
    def pattern(cls, endpoint: str) -> re.Pattern[str]:
        return re.compile(
            rf"{re.escape(cls.stac_prefix.value)}(.*){re.escape(endpoint)}"
        )


CONFORMANCE_URIS = {
    c.name: ConformanceClasses.pattern(c.value) for c in ConformanceClasses
}
