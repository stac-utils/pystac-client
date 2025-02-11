import json
import re
import warnings
from abc import ABC
from collections.abc import Callable, Iterable, Iterator, Mapping
from copy import deepcopy
from datetime import datetime as datetime_
from datetime import timezone
from functools import lru_cache
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Protocol,
    Union,
)

from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc
from pystac import Collection, Item, ItemCollection
from requests import Request

from pystac_client._utils import Modifiable, call_modifier
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
    def __geo_interface__(self) -> dict[str, Any]: ...


DatetimeOrTimestamp = Optional[Union[datetime_, str]]
Datetime = str
DatetimeLike = Union[
    DatetimeOrTimestamp,
    tuple[DatetimeOrTimestamp, DatetimeOrTimestamp],
    list[DatetimeOrTimestamp],
    Iterator[DatetimeOrTimestamp],
]

BBox = tuple[float, ...]
BBoxLike = Union[BBox, list[float], Iterator[float], str]

Collections = tuple[str, ...]
CollectionsLike = Union[list[str], Iterator[str], str]

IDs = tuple[str, ...]
IDsLike = Union[IDs, str, list[str], Iterator[str]]

Intersects = dict[str, Any]
IntersectsLike = Union[str, GeoInterface, Intersects]

Query = dict[str, Any]
QueryLike = Union[Query, list[str]]

FilterLangLike = str
FilterLike = Union[dict[str, Any], str]

Sortby = list[dict[str, str]]
SortbyLike = Union[Sortby, str, list[str]]

Fields = dict[str, list[str]]
FieldsLike = Union[Fields, str, list[str]]

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
    dct: dict[Any, Any], merge_dct: dict[Any, Any], add_keys: bool = True
) -> dict[Any, Any]:
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
        method: str | None = "POST",
        max_items: int | None = None,
        stac_io: StacApiIO | None = None,
        client: Optional["_client.Client"] = None,
        limit: int | None = None,
        ids: IDsLike | None = None,
        collections: CollectionsLike | None = None,
        bbox: BBoxLike | None = None,
        intersects: IntersectsLike | None = None,
        datetime: DatetimeLike | None = None,
        query: QueryLike | None = None,
        filter: FilterLike | None = None,
        filter_lang: FilterLangLike | None = None,
        sortby: SortbyLike | None = None,
        fields: FieldsLike | None = None,
        modifier: Callable[[Modifiable], None] | None = None,
        q: str | None = None,
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

        self._parameters: dict[str, Any] = {
            k: v for k, v in params.items() if v is not None
        }

    def get_parameters(self) -> dict[str, Any]:
        if self.method == "POST":
            return self._parameters
        elif self.method == "GET":
            return self._clean_params_for_get_request()
        else:
            raise Exception(f"Unsupported method {self.method}")

    def _clean_params_for_get_request(self) -> dict[str, Any]:
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

    def _format_query(self, value: QueryLike | None) -> dict[str, Any] | None:
        if value is None:
            return None

        if self.client and not self.client.conforms_to(ConformanceClasses.QUERY):
            warnings.warn(DoesNotConformTo("QUERY"))

        if isinstance(value, dict):
            return value
        elif isinstance(value, list):
            query: dict[str, Any] = {}
            for q in value:
                if isinstance(q, str):
                    try:
                        query = dict_merge(query, json.loads(q))
                    except json.decoder.JSONDecodeError:
                        for op in OPS:
                            parts = q.split(op)
                            if len(parts) == 2:
                                param = parts[0]
                                val: str | float = parts[1]
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
        _filter: FilterLike | None, value: FilterLangLike | None
    ) -> str | None:
        if _filter is None:
            return None

        if value is not None:
            return value

        if isinstance(_filter, str):
            return "cql2-text"

        if isinstance(_filter, dict):
            return "cql2-json"

        return None

    def _format_filter(self, value: FilterLike | None) -> FilterLike | None:
        if value is None:
            return None

        if self.client and not self.client.conforms_to(ConformanceClasses.FILTER):
            warnings.warn(DoesNotConformTo("FILTER"))

        return value

    @staticmethod
    def _format_bbox(value: BBoxLike | None) -> BBox | None:
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
        return f"{dt.isoformat('T')}Z"

    def _to_isoformat_range(
        self,
        component: DatetimeOrTimestamp,
    ) -> tuple[str, str | None]:
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

    def _format_datetime(self, value: DatetimeLike | None) -> Datetime | None:
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
    def _format_collections(value: CollectionsLike | None) -> Collections | None:
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
    def _format_ids(value: IDsLike | None) -> IDs | None:
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

    def _format_sortby(self, value: SortbyLike | None) -> Sortby | None:
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
    def _sortby_part_to_dict(part: str) -> dict[str, str]:
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

    def _format_fields(self, value: FieldsLike | None) -> Fields | None:
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
    def _fields_to_dict(fields: list[str]) -> Fields:
        includes: list[str] = []
        excludes: list[str] = []
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
    def _format_intersects(value: IntersectsLike | None) -> Intersects | None:
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


if TYPE_CHECKING:
    from pystac_client import client as _client


def __getattr__(name: str) -> Any:
    if name in ("DEFAUL_LIMIT", "DEFAULT_LIMIT_AND_MAX_ITEMS"):
        warnings.warn(
            f"{name} is deprecated and will be removed in v0.8", DeprecationWarning
        )
        return 100
    raise AttributeError(f"module {__name__} has no attribute {name}")


class ItemSearch(BaseSearch):
    """Represents a deferred query to a STAC search endpoint as described in the
    `STAC API - Item Search spec
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__.

    No request is sent to the API until a method is called to iterate
    through the resulting STAC Items, either :meth:`ItemSearch.item_collections`,
    :meth:`ItemSearch.items`, or :meth:`ItemSearch.items_as_dicts`.

    All parameters except `url``, ``method``, ``max_items``, and ``client``
    correspond to query parameters
    described in the `STAC API - Item Search: Query Parameters Table
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__
    docs. Please refer
    to those docs for details on how these parameters filter search results.

    Args:
        url: The URL to the search page of the STAC API.
        method : The HTTP method to use when making a request to the service.
            This must be either ``"GET"``, ``"POST"``, or
            ``None``. If ``None``, this will default to ``"POST"``.
            If a ``"POST"`` request receives a ``405`` status for
            the response, it will automatically retry with
            ``"GET"`` for all subsequent requests.
        max_items : The maximum number of items to return from the search, even
            if there are more matching results. This allows the client to limit the
            total number of Items returned from the :meth:`items`,
            :meth:`item_collections`, and :meth:`items_as_dicts methods`. The client
            will continue to request pages of items until the number of max items is
            reached. By default (``max_items=None``) all items matching the query
            will be returned.
        stac_io: An instance of StacIO for retrieving results. Normally comes
            from the Client that returns this ItemSearch client: An instance of a
            root Client used to set the root on resulting Items.
        client: An instance of Client for retrieving results. This is normally populated
            by the client that returns this ItemSearch instance.
        limit: A recommendation to the service as to the number of items to return
            *per page* of results. Defaults to 100.
        ids: List of one or more Item ids to filter on.
        collections: List of one or more Collection IDs or :class:`pystac.Collection`
            instances.
        bbox: A list, tuple, or iterator representing a bounding box of 2D
            or 3D coordinates. Results will be filtered
            to only those intersecting the bounding box.
        intersects: A string or dictionary representing a GeoJSON geometry or feature,
            or an object that implements a ``__geo_interface__`` property, as supported
            by several libraries including Shapely, ArcPy, PySAL, and geojson. Results
            filtered to only those intersecting the geometry.
        datetime: Either a single datetime or datetime range used to filter results.
            You may express a single datetime using a :class:`datetime.datetime`
            instance, a `RFC 3339-compliant <https://tools.ietf.org/html/rfc3339>`__
            timestamp, or a simple date string (see below). Instances of
            :class:`datetime.datetime` may be either
            timezone aware or unaware. Timezone aware instances will be converted to
            a UTC timestamp before being passed
            to the endpoint. Timezone unaware instances are assumed to represent UTC
            timestamps. You may represent a
            datetime range using a ``"/"`` separated string as described in the spec,
            or a list, tuple, or iterator
            of 2 timestamps or datetime instances. For open-ended ranges, use either
            ``".."`` (``'2020-01-01:00:00:00Z/..'``,
            ``['2020-01-01:00:00:00Z', '..']``) or a value of ``None``
            (``['2020-01-01:00:00:00Z', None]``).

            If using a simple date string, the datetime can be specified in
            ``YYYY-mm-dd`` format, optionally truncating
            to ``YYYY-mm`` or just ``YYYY``. Simple date strings will be expanded to
            include the entire time period, for example:

            - ``2017`` expands to ``2017-01-01T00:00:00Z/2017-12-31T23:59:59Z``
            - ``2017-06`` expands to ``2017-06-01T00:00:00Z/2017-06-30T23:59:59Z``
            - ``2017-06-10`` expands to ``2017-06-10T00:00:00Z/2017-06-10T23:59:59Z``

            If used in a range, the end of the range expands to the end of that
            day/month/year, for example:

            - ``2017/2018`` expands to
              ``2017-01-01T00:00:00Z/2018-12-31T23:59:59Z``
            - ``2017-06/2017-07`` expands to
              ``2017-06-01T00:00:00Z/2017-07-31T23:59:59Z``
            - ``2017-06-10/2017-06-11`` expands to
              ``2017-06-10T00:00:00Z/2017-06-11T23:59:59Z``

        query: List or JSON of query parameters as per the STAC API `query` extension
        filter: JSON of query parameters as per the STAC API `filter` extension
        filter_lang: Language variant used in the filter body. If `filter` is a
            dictionary or not provided, defaults
            to 'cql2-json'. If `filter` is a string, defaults to `cql2-text`.
        sortby: A single field or list of fields to sort the response by
        fields: A list of fields to include in the response. Note this may
            result in invalid STAC objects, as they may not have required fields.
            Use `items_as_dicts` to avoid object unmarshalling errors.
        modifier : A callable that modifies the children collection and items
            returned by this Client. This can be useful for injecting
            authentication parameters into child assets to access data
            from non-public sources.

            The callable should expect a single argument, which will be one
            of the following types:

            * :class:`pystac.Collection`
            * :class:`pystac.Item`
            * :class:`pystac.ItemCollection`
            * A STAC item-like :class:`dict`
            * A STAC collection-like :class:`dict`

            The callable should mutate the argument in place and return ``None``.

            ``modifier`` propagates recursively to children of this Client.
            After getting a child collection with, e.g.
            :meth:`Client.get_collection`, the child items of that collection
            will still be signed with ``modifier``.
    """

    _stac_io: StacApiIO

    def __init__(
        self,
        url: str,
        *,
        method: str | None = "POST",
        max_items: int | None = None,
        stac_io: StacApiIO | None = None,
        client: Optional["_client.Client"] = None,
        limit: int | None = None,
        ids: IDsLike | None = None,
        collections: CollectionsLike | None = None,
        bbox: BBoxLike | None = None,
        intersects: IntersectsLike | None = None,
        datetime: DatetimeLike | None = None,
        query: QueryLike | None = None,
        filter: FilterLike | None = None,
        filter_lang: FilterLangLike | None = None,
        sortby: SortbyLike | None = None,
        fields: FieldsLike | None = None,
        modifier: Callable[[Modifiable], None] | None = None,
    ):
        super().__init__(
            url=url,
            method=method,
            max_items=max_items,
            stac_io=stac_io,
            client=client,
            limit=limit,
            ids=ids,
            collections=collections,
            bbox=bbox,
            intersects=intersects,
            datetime=datetime,
            query=query,
            filter=filter,
            filter_lang=filter_lang,
            sortby=sortby,
            fields=fields,
            modifier=modifier,
        )

        if client and client._stac_io is not None and stac_io is None:
            self._stac_io = client._stac_io
            if not client.conforms_to(ConformanceClasses.ITEM_SEARCH):
                warnings.warn(DoesNotConformTo("ITEM_SEARCH"))
        else:
            self._stac_io = stac_io or StacApiIO()

    @lru_cache(1)
    def matched(self) -> int | None:
        """Return number matched for search

        Returns the value from the `numberMatched` or `context.matched` field.
        Not all APIs will support counts in which case a warning will be issued

        Returns:
            int: Total count of matched items. If counts are not supported `None`
            is returned.
        """
        params = {**self.get_parameters(), "limit": 1}
        resp = self._stac_io.read_json(self.url, method=self.method, parameters=params)
        found = None
        if "context" in resp:
            found = resp["context"].get("matched", None)
        elif "numberMatched" in resp:
            found = resp["numberMatched"]
        if found is None:
            warnings.warn("numberMatched or context.matched not in response")
        return found

    # ------------------------------------------------------------------------
    # Result sets
    # ------------------------------------------------------------------------
    # By item
    def items(self) -> Iterator[Item]:
        """Iterator that yields :class:`pystac.Item` instances for each item matching
        the given search parameters.

        Yields:
            Item : each Item matching the search criteria
        """
        for item in self.items_as_dicts():
            # already signed in items_as_dicts
            yield Item.from_dict(item, root=self.client, preserve_dict=False)

    def items_as_dicts(self) -> Iterator[dict[str, Any]]:
        """Iterator that yields :class:`dict` instances for each item matching
        the given search parameters.

        Yields:
            Item : each Item matching the search criteria
        """
        for page in self.pages_as_dicts():
            yield from page.get("features", [])

    # ------------------------------------------------------------------------
    # By Page
    def pages(self) -> Iterator[ItemCollection]:
        """Iterator that yields ItemCollection objects.  Each ItemCollection is
        a page of results from the search.

        Yields:
            ItemCollection : a group of Items matching the search criteria within an
            ItemCollection
        """
        if isinstance(self._stac_io, StacApiIO):
            for page in self.pages_as_dicts():
                # already signed in pages_as_dicts
                yield ItemCollection.from_dict(
                    page, preserve_dict=False, root=self.client
                )

    def pages_as_dicts(self) -> Iterator[dict[str, Any]]:
        """Iterator that yields :class:`dict` instances for each page
        of results from the search.

        Yields:
            Dict : a group of items matching the search
            criteria as a feature-collection-like dictionary.
        """
        if isinstance(self._stac_io, StacApiIO):
            num_items = 0
            for page in self._stac_io.get_pages(
                self.url, self.method, self.get_parameters()
            ):
                call_modifier(self.modifier, page)
                features = page.get("features", [])
                if features:
                    num_items += len(features)
                    if self._max_items and num_items > self._max_items:
                        # Slice the features down to make sure we hit max_items
                        page["features"] = features[0 : -(num_items - self._max_items)]
                    yield page
                    if self._max_items and num_items >= self._max_items:
                        return
                else:
                    return

    # ------------------------------------------------------------------------
    # Everything

    @lru_cache(1)
    def item_collection(self) -> ItemCollection:
        """
        Get the matching items as a :py:class:`pystac.ItemCollection`.

        Return:
            ItemCollection: The item collection
        """
        # Bypass the cache here, so that we can pass __preserve_dict__
        # without mutating what's in the cache.
        feature_collection = self.item_collection_as_dict.__wrapped__(self)
        # already signed in item_collection_as_dict
        return ItemCollection.from_dict(
            feature_collection, preserve_dict=False, root=self.client
        )

    @lru_cache(1)
    def item_collection_as_dict(self) -> dict[str, Any]:
        """
        Get the matching items as an item-collection-like dict.

        The dictionary will have two keys:

        1. ``'type'`` with the value ``'FeatureCollection'``
        2. ``'features'`` with the value being a list of dictionaries
            for the matching items.

        Return:
            Dict : A GeoJSON FeatureCollection
        """
        features = []
        for page in self.pages_as_dicts():
            for feature in page["features"]:
                features.append(feature)
        feature_collection = {"type": "FeatureCollection", "features": features}
        return feature_collection

    # Deprecated methods
    # not caching these, since they're cached in the implementation

    def get_item_collections(self) -> Iterator[ItemCollection]:
        """DEPRECATED

        .. deprecated:: 0.4.0
            Use :meth:`ItemSearch.pages` instead.

        Yields:
            ItemCollection : a group of Items matching the search criteria.
        """
        warnings.warn(
            "get_item_collections() is deprecated, use pages() instead",
            FutureWarning,
        )
        return self.pages()

    def item_collections(self) -> Iterator[ItemCollection]:
        """DEPRECATED

        .. deprecated:: 0.5.0
            Use :meth:`ItemSearch.pages` instead.

        Yields:
            ItemCollection : a group of Items matching the search criteria within an
            ItemCollection
        """
        warnings.warn(
            "item_collections() is deprecated, use pages() instead",
            FutureWarning,
        )
        return self.pages()

    def get_items(self) -> Iterator[Item]:
        """DEPRECATED.

        .. deprecated:: 0.4.0
            Use :meth:`ItemSearch.items` instead.

        Yields:
            Item : each Item matching the search criteria
        """
        warnings.warn(
            "get_items() is deprecated, use items() instead",
            FutureWarning,
        )
        return self.items()

    def get_all_items(self) -> ItemCollection:
        """DEPRECATED

        .. deprecated:: 0.4.0
           Use :meth:`ItemSearch.item_collection` instead.

        Return:
            item_collection : ItemCollection
        """
        warnings.warn(
            "get_all_items() is deprecated, use item_collection() instead.",
            FutureWarning,
        )
        return self.item_collection()

    def get_all_items_as_dict(self) -> dict[str, Any]:
        """DEPRECATED

        .. deprecated:: 0.4.0
           Use :meth:`ItemSearch.item_collection_as_dict` instead.

        Return:
            Dict : A GeoJSON FeatureCollection
        """
        warnings.warn(
            "get_all_items_as_dict() is deprecated, use item_collection_as_dict() "
            "instead.",
            FutureWarning,
        )
        return self.item_collection_as_dict()
