import json
import re
import warnings
from abc import ABC
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import datetime as datetime_
from datetime import timezone
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Tuple,
    Union,
)

from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc
from pystac import Collection
from requests import Request

from pystac_client._utils import Modifiable
from pystac_client.conformance import ConformanceClasses
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import DoesNotConformTo

if TYPE_CHECKING:
    from pystac_client import client as _client

DATETIME_REGEX = re.compile(
    r"^(?P<year>\d{4})(-(?P<month>\d{2})(-(?P<day>\d{2})"
    r"(?P<remainder>([Tt])\d{2}:\d{2}:\d{2}(\.\d+)?"
    r"(?P<tz_info>[Zz]|([-+])(\d{2}):(\d{2}))?)?)?)?$"
)


class GeoInterface(Protocol):
    @property
    def __geo_interface__(self) -> Dict[str, Any]: ...


DatetimeOrTimestamp = Optional[Union[datetime_, str]]
Datetime = str
DatetimeLike = Union[
    DatetimeOrTimestamp,
    Tuple[DatetimeOrTimestamp, DatetimeOrTimestamp],
    List[DatetimeOrTimestamp],
    Iterator[DatetimeOrTimestamp],
]

BBox = Tuple[float, ...]
BBoxLike = Union[BBox, List[float], Iterator[float], str]

Collections = Tuple[str, ...]
CollectionsLike = Union[List[str], Iterator[str], str]

IDs = Tuple[str, ...]
IDsLike = Union[IDs, str, List[str], Iterator[str]]

Intersects = Dict[str, Any]
IntersectsLike = Union[str, GeoInterface, Intersects]

Query = Dict[str, Any]
QueryLike = Union[Query, List[str]]

FilterLangLike = str
FilterLike = Union[Dict[str, Any], str]

Sortby = List[Dict[str, str]]
SortbyLike = Union[Sortby, str, List[str]]

Fields = Dict[str, List[str]]
FieldsLike = Union[Fields, str, List[str]]

# these cannot be reordered or parsing will fail!
OP_MAP = {
    ">=": "gte",
    "<=": "lte",
    "=": "eq",
    "<>": "neq",
    ">": "gt",
    "<": "lt",
}

OPS = list(OP_MAP.keys())


# from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9#gistcomment-2622319
def dict_merge(
    dct: Dict[Any, Any], merge_dct: Dict[Any, Any], add_keys: bool = True
) -> Dict[Any, Any]:
    """Recursive dict merge.

    Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``. This version will return a copy of the dictionary and leave the original
    arguments untouched.  The optional argument ``add_keys``, determines whether keys
    which are present in ``merge_dict`` but not ``dct`` should be included in the new
    dict.

    Args:
        dct (dict) onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys

    Return:
        dict: updated dict
    """
    dct = dct.copy()
    if not add_keys:
        merge_dct = {k: merge_dct[k] for k in set(dct).intersection(set(merge_dct))}

    for k, v in merge_dct.items():
        if k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], Mapping):
            dct[k] = dict_merge(dct[k], merge_dct[k], add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]

    return dct


class BaseSearch(ABC):
    _stac_io: StacApiIO

    def __init__(
        self,
        url: str,
        *,
        method: Optional[str] = "POST",
        max_items: Optional[int] = None,
        stac_io: Optional[StacApiIO] = None,
        client: Optional["_client.Client"] = None,
        limit: Optional[int] = None,
        ids: Optional[IDsLike] = None,
        collections: Optional[CollectionsLike] = None,
        bbox: Optional[BBoxLike] = None,
        intersects: Optional[IntersectsLike] = None,
        datetime: Optional[DatetimeLike] = None,
        query: Optional[QueryLike] = None,
        filter: Optional[FilterLike] = None,
        filter_lang: Optional[FilterLangLike] = None,
        sortby: Optional[SortbyLike] = None,
        fields: Optional[FieldsLike] = None,
        modifier: Optional[Callable[[Modifiable], None]] = None,
        q: Optional[str] = None,
    ):
        self.url = url
        self.client = client

        self._max_items = max_items
        if self._max_items is not None and limit is not None:
            limit = min(limit, self._max_items)

        if limit is not None and (limit < 1 or limit > 10000):
            raise Exception(f"Invalid limit of {limit}, must be between 1 and 10,000")

        self.method = method
        self.modifier = modifier

        params = {
            "limit": limit,
            "bbox": self._format_bbox(bbox),
            "datetime": self._format_datetime(datetime),
            "ids": self._format_ids(ids),
            "collections": self._format_collections(collections),
            "intersects": self._format_intersects(intersects),
            "query": self._format_query(query),
            "filter": self._format_filter(filter),
            "filter-lang": self._format_filter_lang(filter, filter_lang),
            "sortby": self._format_sortby(sortby),
            "fields": self._format_fields(fields),
            "q": q,
        }

        self._parameters: Dict[str, Any] = {
            k: v for k, v in params.items() if v is not None
        }

    def get_parameters(self) -> Dict[str, Any]:
        if self.method == "POST":
            return self._parameters
        elif self.method == "GET":
            return self._clean_params_for_get_request()
        else:
            raise Exception(f"Unsupported method {self.method}")

    def _clean_params_for_get_request(self) -> Dict[str, Any]:
        params = deepcopy(self._parameters)
        if "bbox" in params:
            params["bbox"] = ",".join(map(str, params["bbox"]))
        if "ids" in params:
            params["ids"] = ",".join(params["ids"])
        if "collections" in params:
            params["collections"] = ",".join(params["collections"])
        if "intersects" in params:
            params["intersects"] = json.dumps(
                params["intersects"], separators=(",", ":")
            )
        if "query" in params:
            params["query"] = json.dumps(params["query"], separators=(",", ":"))
        if "sortby" in params:
            params["sortby"] = self._sortby_dict_to_str(params["sortby"])
        if "fields" in params:
            params["fields"] = self._fields_dict_to_str(params["fields"])
        return params

    def url_with_parameters(self) -> str:
        """Returns the search url with parameters, appropriate for a GET request.

        Examples:

        >>> search = ItemSearch(
        ...    url="https://planetarycomputer.microsoft.com/api/stac/v1/search",
        ...    collections=["cop-dem-glo-30"],
        ...    bbox=[88.214, 27.927, 88.302, 28.034],
        ... )
        >>> assert (
        ...    search.url_with_parameters()
        ...    == "https://planetarycomputer.microsoft.com/api/stac/v1/search?"
        ...    "limit=100&bbox=88.214,27.927,88.302,28.034&collections=cop-dem-glo-30"
        ... )

        Returns:
            str: The search url with parameters.
        """
        params = self._clean_params_for_get_request()
        request = Request("GET", self.url, params=params)
        url = request.prepare().url
        if url is None:
            raise ValueError("Could not construct a full url")
        return url

    def _format_query(self, value: Optional[QueryLike]) -> Optional[Dict[str, Any]]:
        if value is None:
            return None

        if self.client and not self.client.conforms_to(ConformanceClasses.QUERY):
            warnings.warn(DoesNotConformTo("QUERY"))

        if isinstance(value, dict):
            return value
        elif isinstance(value, list):
            query: Dict[str, Any] = {}
            for q in value:
                if isinstance(q, str):
                    try:
                        query = dict_merge(query, json.loads(q))
                    except json.decoder.JSONDecodeError:
                        for op in OPS:
                            parts = q.split(op)
                            if len(parts) == 2:
                                param = parts[0]
                                val: Union[str, float] = parts[1]
                                if param == "gsd":
                                    val = float(val)
                                query = dict_merge(query, {parts[0]: {OP_MAP[op]: val}})
                                break
                else:
                    raise Exception("Unsupported query format, must be a List[str].")
        else:
            raise Exception("Unsupported query format, must be a Dict or List[str].")

        return query

    @staticmethod
    def _format_filter_lang(
        _filter: Optional[FilterLike], value: Optional[FilterLangLike]
    ) -> Optional[str]:
        if _filter is None:
            return None

        if value is not None:
            return value

        if isinstance(_filter, str):
            return "cql2-text"

        if isinstance(_filter, dict):
            return "cql2-json"

        return None

    def _format_filter(self, value: Optional[FilterLike]) -> Optional[FilterLike]:
        if value is None:
            return None

        if self.client and not self.client.conforms_to(ConformanceClasses.FILTER):
            warnings.warn(DoesNotConformTo("FILTER"))

        return value

    @staticmethod
    def _format_bbox(value: Optional[BBoxLike]) -> Optional[BBox]:
        if value is None:
            return None

        if isinstance(value, str):
            bbox = tuple(map(float, value.split(",")))
        else:
            bbox = tuple(map(float, value))

        return bbox

    @staticmethod
    def _to_utc_isoformat(dt: datetime_) -> str:
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        dt = dt.replace(tzinfo=None)
        return f'{dt.isoformat("T")}Z'

    def _to_isoformat_range(
        self,
        component: DatetimeOrTimestamp,
    ) -> Tuple[str, Optional[str]]:
        """Converts a single DatetimeOrTimestamp into one or two Datetimes.

        This is required to expand a single value like "2017" out to the whole
        year. This function returns two values. The first value is always a
        valid Datetime. The second value can be None or a Datetime. If it is
        None, this means that the first value was an exactly specified value
        (e.g. a `datetime.datetime`). If the second value is a Datetime, then
        it will be the end of the range at the resolution of the component,
        e.g. if the component were "2017" the second value would be the last
        second of the last day of 2017.
        """
        if component is None:
            return "..", None
        elif isinstance(component, str):
            if component == "..":
                return component, None
            elif component == "":
                return "..", None

            match = DATETIME_REGEX.match(component)
            if not match:
                raise Exception(f"invalid datetime component: {component}")
            elif match.group("remainder"):
                if match.group("tz_info"):
                    return component, None
                else:
                    return f"{component}Z", None
            else:
                year = int(match.group("year"))
                optional_month = match.group("month")
                optional_day = match.group("day")

            if optional_day is not None:
                start = datetime_(
                    year,
                    int(optional_month),
                    int(optional_day),
                    0,
                    0,
                    0,
                    tzinfo=tzutc(),
                )
                end = start + relativedelta(days=1, seconds=-1)
            elif optional_month is not None:
                start = datetime_(year, int(optional_month), 1, 0, 0, 0, tzinfo=tzutc())
                end = start + relativedelta(months=1, seconds=-1)
            else:
                start = datetime_(year, 1, 1, 0, 0, 0, tzinfo=tzutc())
                end = start + relativedelta(years=1, seconds=-1)
            return self._to_utc_isoformat(start), self._to_utc_isoformat(end)
        else:
            return self._to_utc_isoformat(component), None

    def _format_datetime(self, value: Optional[DatetimeLike]) -> Optional[Datetime]:
        if value is None:
            return None
        elif isinstance(value, datetime_):
            return self._to_utc_isoformat(value)
        elif isinstance(value, str):
            components = value.split("/")
        else:
            components = list(value)  # type: ignore

        if not components:
            return None
        elif len(components) == 1:
            if components[0] is None:
                raise Exception("cannot create a datetime query with None")
            start, end = self._to_isoformat_range(components[0])
            if end is not None:
                return f"{start}/{end}"
            else:
                return start
        elif len(components) == 2:
            if all(c is None for c in components):
                raise Exception("cannot create a double open-ended interval")
            start, _ = self._to_isoformat_range(components[0])
            backup_end, end = self._to_isoformat_range(components[1])
            return f"{start}/{end or backup_end}"
        else:
            raise Exception(
                "too many datetime components "
                f"(max=2, actual={len(components)}): {value}"
            )

    @staticmethod
    def _format_collections(value: Optional[CollectionsLike]) -> Optional[Collections]:
        def _format(c: Any) -> Collections:
            if isinstance(c, str):
                return (c,)
            if isinstance(c, Iterable):
                return tuple(map(lambda x: _format(x)[0], c))

            return (c.id,)

        if value is None:
            return None
        if isinstance(value, str):
            return tuple(map(lambda x: _format(x)[0], value.split(",")))
        if isinstance(value, Collection):
            return _format(value)

        return _format(value)

    @staticmethod
    def _format_ids(value: Optional[IDsLike]) -> Optional[IDs]:
        if value is None or isinstance(value, (tuple, list)) and not value:
            # We can't just check for truthiness here because of the Iterator[str] case
            return None
        elif isinstance(value, str):
            # We could check for str in the first branch, but then we'd be checking
            # for str twice #microoptimizations
            if value:
                return tuple(value.split(","))
            else:
                return None
        else:
            return tuple(value)

    def _format_sortby(self, value: Optional[SortbyLike]) -> Optional[Sortby]:
        if value is None:
            return None

        if self.client and not self.client.conforms_to(ConformanceClasses.SORT):
            warnings.warn(DoesNotConformTo("SORT"))

        if isinstance(value, str):
            return [self._sortby_part_to_dict(part) for part in value.split(",")]

        if isinstance(value, list):
            if value and isinstance(value[0], str):
                return [self._sortby_part_to_dict(str(v)) for v in value]
            elif value and isinstance(value[0], dict):
                return value  # type: ignore

        raise Exception(
            "sortby must be of type None, str, List[str], or List[Dict[str, str]"
        )

    @staticmethod
    def _sortby_part_to_dict(part: str) -> Dict[str, str]:
        if part.startswith("-"):
            return {"field": part[1:], "direction": "desc"}
        elif part.startswith("+"):
            return {"field": part[1:], "direction": "asc"}
        else:
            return {"field": part, "direction": "asc"}

    @staticmethod
    def _sortby_dict_to_str(sortby: Sortby) -> str:
        return ",".join(
            [
                f"{'+' if sort['direction'] == 'asc' else '-'}{sort['field']}"
                for sort in sortby
            ]
        )

    def _format_fields(self, value: Optional[FieldsLike]) -> Optional[Fields]:
        if value is None:
            return None

        if self.client and not self.client.conforms_to(ConformanceClasses.FIELDS):
            warnings.warn(DoesNotConformTo("FIELDS"))

        if isinstance(value, str):
            return self._fields_to_dict(value.split(","))
        if isinstance(value, list):
            return self._fields_to_dict(value)
        if isinstance(value, dict):
            return value

        raise Exception(
            "sortby must be of type None, str, List[str], or List[Dict[str, str]"
        )

    @staticmethod
    def _fields_to_dict(fields: List[str]) -> Fields:
        includes: List[str] = []
        excludes: List[str] = []
        for field in fields:
            if field.startswith("-"):
                excludes.append(field[1:])
            elif field.startswith("+"):
                includes.append(field[1:])
            else:
                includes.append(field)
        return {"include": includes, "exclude": excludes}

    @staticmethod
    def _fields_dict_to_str(fields: Fields) -> str:
        includes = [f"+{x}" for x in fields.get("include", [])]
        excludes = [f"-{x}" for x in fields.get("exclude", [])]
        return ",".join(chain(includes, excludes))

    @staticmethod
    def _format_intersects(value: Optional[IntersectsLike]) -> Optional[Intersects]:
        if value is None:
            return None
        if isinstance(value, dict):
            if value.get("type") == "Feature":
                return deepcopy(value.get("geometry"))
            else:
                return deepcopy(value)
        if isinstance(value, str):
            return dict(json.loads(value))
        if hasattr(value, "__geo_interface__"):
            return dict(deepcopy(getattr(value, "__geo_interface__")))
        raise Exception(
            "intersects must be of type None, str, dict, or an object that "
            "implements __geo_interface__"
        )
