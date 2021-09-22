from dateutil.tz import tzutc
from dateutil.relativedelta import relativedelta
import json
import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import timezone, datetime as datetime_
from typing import Dict, Iterator, List, Optional, TYPE_CHECKING, Tuple, Union
import warnings

from pystac import Collection, Item, ItemCollection
from pystac.stac_io import StacIO

from pystac_client.stac_api_io import StacApiIO
from pystac_client.conformance import ConformanceClasses

if TYPE_CHECKING:
    from pystac_client.client import Client

DATETIME_REGEX = re.compile(r"(?P<year>\d{4})(\-(?P<month>\d{2})(\-(?P<day>\d{2})"
                            r"(?P<remainder>(T|t)\d{2}:\d{2}:\d{2}(\.\d+)?"
                            r"(?P<tz_info>Z|([-+])(\d{2}):(\d{2}))?)?)?)?")

DatetimeOrTimestamp = Optional[Union[datetime_, str]]
Datetime = Union[Tuple[str], Tuple[str, str]]
DatetimeLike = Union[DatetimeOrTimestamp, Tuple[DatetimeOrTimestamp, DatetimeOrTimestamp],
                     List[DatetimeOrTimestamp], Iterator[DatetimeOrTimestamp]]

BBox = Tuple[float, ...]
BBoxLike = Union[BBox, List[float], Iterator[float], str]

Collections = Tuple[str, ...]
CollectionsLike = Union[List[str], Iterator[str], str]

IDs = Tuple[str, ...]
IDsLike = Union[IDs, str, List[str], Iterator[str]]

Intersects = dict
IntersectsLike = Union[str, Intersects, object]

Query = dict
QueryLike = Union[Query, List[str]]

FilterLike = dict

Sortby = List[str]
SortbyLike = Union[Sortby, str]

Fields = List[str]
FieldsLike = Union[Fields, str]


# from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9#gistcomment-2622319
def dict_merge(dct: Dict, merge_dct: Dict, add_keys: bool = True) -> Dict:
    """ Recursive dict merge.

    Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``. This version will return a copy of the dictionary and leave the original
    arguments untouched.  The optional argument ``add_keys``, determines whether keys which are
    present in ``merge_dict`` but not ``dct`` should be included in the new dict.

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
        if (k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], Mapping)):
            dct[k] = dict_merge(dct[k], merge_dct[k], add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]

    return dct


class ItemSearch:
    """Represents a deferred query to a STAC search endpoint as described in the
    `STAC API - Item Search spec <https://github.com/radiantearth/stac-api-spec/tree/master/item-search>`__.

    No request is sent to the API until a function is called to fetch or iterate through the resulting STAC Items,
     either the :meth:`ItemSearch.item_collections` or :meth:`ItemSearch.items` method is called and iterated over.

    All "Parameters", with the exception of ``max_items``, ``method``, and ``url`` correspond to query parameters
    described in the `STAC API - Item Search: Query Parameters Table
    <https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__ docs. Please refer
    to those docs for details on how these parameters filter search results.

    Args:
        url : The URL to the item-search endpoint
        method : The HTTP method to use when making a request to the service. This must be either ``"GET"``, ``"POST"``, or
            ``None``. If ``None``, this will default to ``"POST"`` if the ``intersects`` argument is present and ``"GET"``
            if not. If a ``"POST"`` request receives a ``405`` status for the response, it will automatically retry with a
            ``"GET"`` request for all subsequent requests.
        max_items : The maximum number of items to return from the search. *Note that this is not a STAC API - Item Search
            parameter and is instead used by the client to limit the total number of returned items*.
        limit : The maximum number of items to return *per page*. Defaults to ``None``, which falls back to the limit set
            by the service.
        bbox: May be a list, tuple, or iterator representing a bounding box of 2D or 3D coordinates. Results will be filtered
            to only those intersecting the bounding box.
        datetime: Either a single datetime or datetime range used to filter results. You may express a single datetime
            using a :class:`datetime.datetime` instance, a `RFC 3339-compliant <https://tools.ietf.org/html/rfc3339>`__
            timestamp, or a simple date string (see below). Instances of :class:`datetime.datetime` may be either
            timezone aware or unaware. Timezone aware instances will be converted to a UTC timestamp before being passed
            to the endpoint. Timezone unaware instances are assumed to represent UTC timestamps. You may represent a
            datetime range using a ``"/"`` separated string as described in the spec, or a list, tuple, or iterator
            of 2 timestamps or datetime instances. For open-ended ranges, use either ``".."`` (``'2020-01-01:00:00:00Z/..'``,
            ``['2020-01-01:00:00:00Z', '..']``) or a value of ``None`` (``['2020-01-01:00:00:00Z', None]``).

            If using a simple date string, the datetime can be specified in ``YYYY-mm-dd`` format, optionally truncating
            to ``YYYY-mm`` or just ``YYYY``. Simple date strings will be expanded to include the entire time period, for
            example:

            - ``2017`` expands to ``2017-01-01T00:00:00Z/2017-12-31T23:59:59Z``
            - ``2017-06`` expands to ``2017-06-01T00:00:00Z/2017-06-30T23:59:59Z``
            - ``2017-06-10`` expands to ``2017-06-10T00:00:00Z/2017-06-10T23:59:59Z``

            If used in a range, the end of the range expands to the end of that day/month/year, for example:

            - ``2017/2018`` expands to ``2017-01-01T00:00:00Z/2018-12-31T23:59:59Z``
            - ``2017-06/2017-07`` expands to ``2017-06-01T00:00:00Z/2017-07-31T23:59:59Z``
            - ``2017-06-10/2017-06-11`` expands to ``2017-06-10T00:00:00Z/2017-06-11T23:59:59Z``
        intersects: A GeoJSON-like dictionary or JSON string. Results filtered to only those intersecting the geometry
        ids: List of Item ids to return. All other filter parameters that further restrict the number of search results
            (except ``limit``) are ignored.
        collections: List of one or more Collection IDs or :class:`pystac.Collection` instances. Only Items in one
            of the provided Collections will be searched
        query: List or JSON of query parameters as per the STAC API `query` extension
        filter: JSON of query parameters as per the STAC API `filter` extension
        sortby: A single field or list of fields to sort the response by
        fields: A list of fields to return in the response. Note this may result in invalid JSON.
            Use `get_all_items_as_dict` to avoid errors
        max_items: The maximum number of items to get, even if there are more matched items
        method: The http method, 'GET' or 'POST'
        stac_io: An instance of of StacIO for retrieving results. Normally comes from the Client that returns this ItemSearch
        client: An instance of a root Client used to set the root on resulting Items
    """
    def __init__(self,
                 url: str,
                 *,
                 limit: Optional[int] = None,
                 bbox: Optional[BBoxLike] = None,
                 datetime: Optional[DatetimeLike] = None,
                 intersects: Optional[IntersectsLike] = None,
                 ids: Optional[IDsLike] = None,
                 collections: Optional[CollectionsLike] = None,
                 query: Optional[QueryLike] = None,
                 filter: Optional[FilterLike] = None,
                 sortby: Optional[SortbyLike] = None,
                 fields: Optional[FieldsLike] = None,
                 max_items: Optional[int] = None,
                 method: Optional[str] = 'POST',
                 stac_io: Optional[StacIO] = None,
                 client: Optional["Client"] = None):
        self.url = url
        self.client = client

        if stac_io:
            self._stac_io = stac_io
        else:
            self._stac_io = StacApiIO()
        self._stac_io.assert_conforms_to(ConformanceClasses.ITEM_SEARCH)

        self._max_items = max_items
        if self._max_items is not None and limit is not None:
            limit = min(limit, self._max_items)

        if limit is not None and (limit < 1 or limit > 10000):
            raise Exception(f"Invalid limit of {limit}, must be between 1 and 10,000")

        self.method = method

        params = {
            'limit': limit,
            'bbox': self._format_bbox(bbox),
            'datetime': self._format_datetime(datetime),
            'ids': self._format_ids(ids),
            'collections': self._format_collections(collections),
            'intersects': self._format_intersects(intersects),
            'query': self._format_query(query),
            'filter': self._format_filter(filter),
            'sortby': self._format_sortby(sortby),
            'fields': self._format_fields(fields)
        }

        if params['filter'] is not None:
            params['filter-lang'] = 'cql-json'

        self._parameters = {k: v for k, v in params.items() if v is not None}

    def get_parameters(self):
        if self.method == 'POST':
            return self._parameters
        elif self.method == 'GET':
            params = deepcopy(self._parameters)
            if 'bbox' in params:
                params['bbox'] = ','.join(params['bbox'])
            if 'ids' in params:
                params['ids'] = ','.join(params['ids'])
            if 'collections' in params:
                params['collections'] = ','.join(params['collections'])
            if 'intersects' in params:
                params['intersects'] = json.dumps(params['intersects'])
            return params
        else:
            raise Exception(f"Unsupported method {self.method}")

    @staticmethod
    def _format_query(value: List[QueryLike]) -> Optional[dict]:
        if value is None:
            return None

        OP_MAP = {'>=': 'gte', '<=': 'lte', '=': 'eq', '>': 'gt', '<': 'lt'}

        if isinstance(value, list):
            query = {}
            for q in value:
                for op in ['>=', '<=', '=', '>', '<']:
                    parts = q.split(op)
                    if len(parts) == 2:
                        param = parts[0]
                        val = parts[1]
                        if param == "gsd":
                            val = float(val)
                        query = dict_merge(query, {parts[0]: {OP_MAP[op]: val}})
                        break
        else:
            query = value

        return query

    def _format_filter(self, value: FilterLike) -> Optional[dict]:
        if value is None:
            return None

        self._stac_io.assert_conforms_to(ConformanceClasses.FILTER)
        return value

    @staticmethod
    def _format_bbox(value: Optional[BBoxLike]) -> Optional[BBox]:
        if value is None:
            return None

        if isinstance(value, str):
            bbox = tuple(map(float, value.split(',')))
        else:
            bbox = tuple(map(float, value))

        return bbox

    @staticmethod
    def _format_datetime(value: Optional[DatetimeLike]) -> Optional[Datetime]:
        def _to_utc_isoformat(dt):
            dt = dt.astimezone(timezone.utc)
            dt = dt.replace(tzinfo=None)
            return dt.isoformat("T") + "Z"

        def _to_isoformat_range(component: DatetimeOrTimestamp):
            """Converts a single DatetimeOrTimestamp into one or two Datetimes.

            This is required to expand a single value like "2017" out to the whole year. This function returns two values.
            The first value is always a valid Datetime. The second value can be None or a Datetime. If it is None, this
            means that the first value was an exactly specified value (e.g. a `datetime.datetime`). If the second value is
            a Datetime, then it will be the end of the range at the resolution of the component, e.g. if the component
            were "2017" the second value would be the last second of the last day of 2017.
            """
            if component is None:
                return "..", None
            elif isinstance(component, str):
                if component == "..":
                    return component, None

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
                    start = datetime_(year,
                                      int(optional_month),
                                      int(optional_day),
                                      0,
                                      0,
                                      0,
                                      tzinfo=tzutc())
                    end = start + relativedelta(days=1, seconds=-1)
                elif optional_month is not None:
                    start = datetime_(year, int(optional_month), 1, 0, 0, 0, tzinfo=tzutc())
                    end = start + relativedelta(months=1, seconds=-1)
                else:
                    start = datetime_(year, 1, 1, 0, 0, 0, tzinfo=tzutc())
                    end = start + relativedelta(years=1, seconds=-1)
                return _to_utc_isoformat(start), _to_utc_isoformat(end)
            else:
                return _to_utc_isoformat(component), None

        if value is None:
            return None
        elif isinstance(value, datetime_):
            return _to_utc_isoformat(value)
        elif isinstance(value, str):
            components = value.split("/")
        else:
            components = list(value)

        if not components:
            return None
        elif len(components) == 1:
            start, end = _to_isoformat_range(components[0])
            if end is not None:
                return f"{start}/{end}"
            else:
                return start
        elif len(components) == 2:
            start, _ = _to_isoformat_range(components[0])
            backup_end, end = _to_isoformat_range(components[1])
            return f"{start}/{end or backup_end}"
        else:
            raise Exception(
                f"too many datetime components (max=2, actual={len(components)}): {value}")

    @staticmethod
    def _format_collections(value: Optional[CollectionsLike]) -> Optional[Collections]:
        def _format(c):
            if isinstance(c, str):
                return c
            if isinstance(c, Iterable):
                return tuple(map(_format, c))

            return c.id

        if value is None:
            return None
        if isinstance(value, str):
            return tuple(map(_format, value.split(',')))
        if isinstance(value, Collection):
            return _format(value),

        return _format(value)

    @staticmethod
    def _format_ids(value: Optional[IDsLike]) -> Optional[IDs]:
        if value is None:
            return None

        if isinstance(value, str):
            return tuple(value.split(','))

        return tuple(value)

    def _format_sortby(self, value: Optional[SortbyLike]) -> Optional[Sortby]:
        if value is None:
            return None

        self._stac_io.assert_conforms_to(ConformanceClasses.SORT)

        if isinstance(value, str):
            return tuple(value.split(','))

        return tuple(value)

    def _format_fields(self, value: Optional[FieldsLike]) -> Optional[Fields]:
        if value is None:
            return None

        self._stac_io.assert_conforms_to(ConformanceClasses.FIELDS)

        if isinstance(value, str):
            return tuple(value.split(','))

        return tuple(value)

    @staticmethod
    def _format_intersects(value: Optional[IntersectsLike]) -> Optional[Intersects]:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return deepcopy(getattr(value, '__geo_interface__', value))

    def matched(self) -> int:
        """Return number matched for search

        Returns the value from the `numberMatched` or `context.matched` field. Not all APIs
        will support counts in which case a warning will be issued

        Returns:
            int: Total count of matched items. If counts are not supported `None` is returned.
        """
        params = {**self.get_parameters(), "limit": 1}
        resp = self._stac_io.read_json(self.url, method=self.method, parameters=params)
        found = None
        if 'context' in resp:
            found = resp['context']['matched']
        elif 'numberMatched' in resp:
            found = resp['numberMatched']
        if found is None:
            warnings.warn("numberMatched or context.matched not in response")
        return found

    def get_item_collections(self) -> Iterator[ItemCollection]:
        """Iterator that yields ItemCollection objects.  Each ItemCollection is a page of results
        from the search.

        Yields:
            Iterable[Item] : pystac_client.ItemCollection
        """
        for page in self._stac_io.get_pages(self.url, self.method, self.get_parameters()):
            yield ItemCollection.from_dict(page, preserve_dict=False, root=self.client)

    def get_items(self) -> Iterator[Item]:
        """Iterator that yields :class:`pystac.Item` instances for each item matching the given search parameters. Calls
        :meth:`ItemSearch.item_collections()` internally and yields from
        :attr:`ItemCollection.features <pystac_client.ItemCollection.features>` for each page of results.

        Return:
            Iterable[Item] : Iterate through resulting Items
        """
        nitems = 0
        for item_collection in self.get_item_collections():
            for item in item_collection:
                yield item
                nitems += 1
                if self._max_items and nitems >= self._max_items:
                    return

    def get_all_items_as_dict(self) -> Dict:
        """Convenience method that gets all items from all pages, up to self._max_items,
         and returns an array of dictionaries

        Return:
            Dict : A GeoJSON FeatureCollection
        """
        features = []
        for page in self._stac_io.get_pages(self.url, self.method, self.get_parameters()):
            for feature in page['features']:
                features.append(feature)
                if self._max_items and len(features) >= self._max_items:
                    return {"type": "FeatureCollection", "features": features}
        return {"type": "FeatureCollection", "features": features}

    def get_all_items(self) -> ItemCollection:
        """Convenience method that builds an :class:`ItemCollection` from all items matching the given search parameters.

        Return:
            item_collection : ItemCollection
        """
        feature_collection = self.get_all_items_as_dict()
        return ItemCollection.from_dict(feature_collection, preserve_dict=False, root=self.client)
