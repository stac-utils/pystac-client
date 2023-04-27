from __future__ import annotations

import re
from enum import Enum


class ConformanceClasses(Enum):
    """Enumeration class for Conformance Classes"""

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
    def get_by_name(cls, name: str) -> ConformanceClasses:
        for member in cls:
            if member.name == name.upper():
                return member
        raise ValueError(
            f"Invalid conformance class '{name}'. Options are: {list(cls)}"
        )

    def __str__(self) -> str:
        return f"{self.name}"

    def __repr__(self) -> str:
        return str(self)

    @property
    def valid_uri(self) -> str:
        return f"https://api.stacspec.org/v1.0.*{self.value}"

    @property
    def pattern(self) -> re.Pattern[str]:
        return re.compile(
            rf"{re.escape('https://api.stacspec.org/v1.0.')}(.*){re.escape(self.value)}"
        )
