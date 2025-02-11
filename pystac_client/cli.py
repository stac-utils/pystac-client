import argparse
import json
import logging
import os
import re
import sys
import warnings
from typing import Any

from pystac import STACError, STACTypeError

from .client import Client
from .conformance import ConformanceClasses
from .item_search import (
    OPS,
    BBoxLike,
    CollectionsLike,
    DatetimeLike,
    FieldsLike,
    FilterLangLike,
    FilterLike,
    IDsLike,
    IntersectsLike,
    QueryLike,
    SortbyLike,
)
from .version import __version__
from .warnings import (
    DoesNotConformTo,
    FallbackToPystac,
    MissingLink,
    NoConformsTo,
    PystacClientWarning,
)

logger = logging.getLogger(__name__)


def search(
    client: Client,
    matched: bool = False,
    save: str | None = None,
    *,
    method: str = "GET",
    max_items: int | None = None,
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
) -> int:
    """Main function for performing a search"""

    result = client.search(
        method=method,
        max_items=max_items,
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
    )

    if matched:
        if (nmatched := result.matched()) is not None:
            print(f"{nmatched} items matched")
        else:
            raise KeyError("'matched' is not supported for this catalog")
    else:
        feature_collection = result.item_collection_as_dict()
        if save:
            with open(save, "w") as f:
                f.write(json.dumps(feature_collection))
        else:
            print(json.dumps(feature_collection))
    return 0


def collections(
    client: Client,
    save: str | None = None,
    matched: bool = False,
    *,
    max_collections: int | None = None,
    limit: int | None = None,
    bbox: BBoxLike | None = None,
    datetime: DatetimeLike | None = None,
    q: str | None = None,
    query: QueryLike | None = None,
    filter: FilterLike | None = None,
    filter_lang: FilterLangLike | None = None,
    sortby: SortbyLike | None = None,
    fields: FieldsLike | None = None,
) -> int:
    """Fetch collections from collections endpoint"""
    try:
        result = client.collection_search(
            max_collections=max_collections,
            limit=limit,
            bbox=bbox,
            datetime=datetime,
            q=q,
            query=query,
            filter=filter,
            filter_lang=filter_lang,
            sortby=sortby,
            fields=fields,
        )
        if matched:
            if (nmatched := result.matched()) is not None:
                print(f"{nmatched} collections matched")
            else:
                raise KeyError("'matched' is not supported for this catalog")
        else:
            collections_dicts = list(result.collections_as_dicts())
            if save:
                with open(save, "w") as f:
                    f.write(json.dumps(collections_dicts))
            else:
                print(json.dumps(collections_dicts))
    except STACTypeError as e:
        raise STACError(
            f"The client at {client.self_href} is OK, but one or more of the "
            "collections is invalid."
        ) from e
    return 0


def add_warnings_behavior(parser: argparse.ArgumentParser) -> None:
    warnings_group = parser.add_argument_group("warnings behavior")
    warnings_group.add_argument(
        "--error",
        nargs="*",
        choices=[
            "no-conforms-to",
            "does-not-conform-to",
            "missing-link",
            "fallback-to-pystac",
        ],
        help="Error on all stac-client warnings or specific warnings.",
    )
    warnings_group.add_argument(
        "--ignore",
        nargs="*",
        choices=[
            "no-conforms-to",
            "does-not-conform-to",
            "missing-link",
            "fallback-to-pystac",
        ],
        help="Ignore all stac-client warnings or specific warnings.",
    )


def set_warnings(error: list[str] | None, ignore: list[str] | None) -> None:
    # First set filters on the base class
    if ignore is not None and len(ignore) == 0:
        warnings.filterwarnings("ignore", category=PystacClientWarning)
    if error is not None and len(error) == 0:
        warnings.filterwarnings("error", category=PystacClientWarning)

    # Then set filters on any specific classes
    category_options = {
        "no-conforms-to": NoConformsTo,
        "does-not-conform-to": DoesNotConformTo,
        "missing-link": MissingLink,
        "fallback-to-pystac": FallbackToPystac,
    }
    if ignore is not None:
        for w in ignore:
            warnings.filterwarnings("ignore", category=category_options[w])
    if error is not None:
        for w in error:
            warnings.filterwarnings("error", category=category_options[w])


def set_conforms_to(
    client: Client, clear: bool, remove: list[str] | None, add: list[str] | None
) -> None:
    """Alters conforms_to settings on client in-place"""
    if clear:
        client.clear_conforms_to()
    if remove is not None:
        for conformance_class in remove:
            client.remove_conforms_to(conformance_class)
    if add is not None:
        for conformance_class in add:
            client.add_conforms_to(conformance_class)


def parse_args(args: list[str]) -> dict[str, Any]:
    desc = "STAC Client"
    dhf = argparse.ArgumentDefaultsHelpFormatter
    parser0 = argparse.ArgumentParser(description=desc)
    parser0.add_argument(
        "--version",
        help="Print version and exit",
        action="version",
        version=__version__,
    )

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("url", help="Root Catalog URL")
    parent.add_argument(
        "--logging", default="INFO", help="DEBUG, INFO, WARN, ERROR, CRITICAL"
    )
    parent.add_argument(
        "--headers",
        nargs="*",
        help="Additional request headers (KEY=VALUE pairs)",
        default=None,
    )
    parent.add_argument(
        "--add-conforms-to",
        choices=[c.name for c in ConformanceClasses],
        nargs="*",
        help="Specify conformance classes to add to client",
    )
    parent.add_argument(
        "--remove-conforms-to",
        choices=[c.name for c in ConformanceClasses],
        nargs="*",
        help="Specify conformance classes to remove from client",
    )
    parent.add_argument(
        "--clear-conforms-to",
        default=False,
        action="store_true",
    )

    subparsers = parser0.add_subparsers(dest="command")

    # collections command
    parser = subparsers.add_parser(
        "collections",
        help="Get all collections in this Catalog",
        parents=[parent],
        formatter_class=dhf,
    )
    add_warnings_behavior(parser)

    collections_group = parser.add_argument_group("collection search options")
    collections_group.add_argument(
        "--bbox", help="Bounding box (min lon, min lat, max lon, max lat)", nargs=4
    )
    collections_group.add_argument(
        "--datetime",
        help="Single datetime or begin and end datetime (e.g., 2017-01-01/2017-02-15)",
    )
    collections_group.add_argument("--q", help="Free-text search query")
    collections_group.add_argument(
        "--query",
        nargs="*",
        help=f"Query properties of form KEY=VALUE ({','.join(OPS)} supported)",
    )
    collections_group.add_argument(
        "--filter",
        help="Filter on queryables using language specified in filter-lang parameter",
    )
    collections_group.add_argument(
        "--filter-lang",
        help="Filter language used within the filter parameter",
        default="cql2-json",
    )
    collections_group.add_argument("--sortby", help="Sort by fields", nargs="*")
    collections_group.add_argument(
        "--fields", help="Control what fields get returned", nargs="*"
    )
    collections_group.add_argument("--limit", help="Page size limit", type=int)
    collections_group.add_argument(
        "--max-collections",
        dest="max_collections",
        help="Max collections to retrieve from search",
        type=int,
    )

    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "--save", help="Filename to save collections to", default=None
    )
    output_group.add_argument(
        "--matched", help="Print number matched", default=False, action="store_true"
    )

    # search command
    parser = subparsers.add_parser(
        "search",
        help="Perform new search of items",
        parents=[parent],
        formatter_class=dhf,
    )

    search_group = parser.add_argument_group("search options")
    search_group.add_argument(
        "-c", "--collections", help="One or more collection IDs", nargs="*"
    )
    search_group.add_argument(
        "--ids", help="One or more Item IDs (ignores other parameters)", nargs="*"
    )
    search_group.add_argument(
        "--bbox", help="Bounding box (min lon, min lat, max lon, max lat)", nargs=4
    )
    search_group.add_argument(
        "--intersects", help="GeoJSON Feature or geometry (file or string)"
    )
    search_group.add_argument(
        "--datetime",
        help="Single datetime or begin and end datetime (e.g., 2017-01-01/2017-02-15)",
    )
    search_group.add_argument(
        "--query",
        nargs="*",
        help=f"Query properties of form KEY=VALUE ({','.join(OPS)} supported)",
    )
    search_group.add_argument(
        "--filter",
        help="Filter on queryables using language specified in filter-lang parameter",
    )
    search_group.add_argument(
        "--filter-lang",
        help="Filter language used within the filter parameter",
        default="cql2-json",
    )
    search_group.add_argument("--sortby", help="Sort by fields", nargs="*")
    search_group.add_argument(
        "--fields", help="Control what fields get returned", nargs="*"
    )
    search_group.add_argument("--limit", help="Page size limit", type=int)
    search_group.add_argument(
        "--max-items",
        dest="max_items",
        help="Max items to retrieve from search",
        type=int,
    )
    search_group.add_argument("--method", help="GET or POST", default="POST")
    add_warnings_behavior(parser)

    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "--matched", help="Print number matched", default=False, action="store_true"
    )
    output_group.add_argument(
        "--save", help="Filename to save Item collection to", default=None
    )

    parsed_args = {
        k: v for k, v in vars(parser0.parse_args(args)).items() if v is not None
    }
    if "command" not in parsed_args:
        parser0.print_usage()
        return {}

    # if intersects is JSON file, read it in
    if "intersects" in parsed_args:
        if os.path.exists(parsed_args["intersects"]):
            with open(parsed_args["intersects"]) as f:
                data = json.loads(f.read())
                if data["type"] == "Feature":
                    parsed_args["intersects"] = data["geometry"]
                elif data["type"] == "FeatureCollection":
                    logger.warning(
                        "When the input to intersects is a FeatureCollection, "
                        "only the first feature geometry is used."
                    )
                    parsed_args["intersects"] = data["features"][0]["geometry"]
                else:
                    parsed_args["intersects"] = data

    # if headers provided, parse it
    if "headers" in parsed_args:
        new_headers = {}
        splitter = re.compile("^([^=]+)=(.+)$")
        for head in parsed_args["headers"]:
            match = splitter.match(head)
            if match:
                new_headers[match.group(1)] = match.group(2)
            else:
                logger.warning(f"Unable to parse header {head}")
        parsed_args["headers"] = new_headers

    if "filter" in parsed_args:
        if "json" in parsed_args["filter_lang"]:
            parsed_args["filter"] = json.loads(parsed_args["filter"])

    return parsed_args


def cli() -> int:
    args = parse_args(sys.argv[1:])
    if not args:
        return 1

    loglevel = args.pop("logging")
    if args.get("save", False) or args.get("matched", False):
        logging.basicConfig(level=loglevel)
        # quiet loggers
        logging.getLogger("urllib3").propagate = False

    cmd = args.pop("command")

    try:
        url = args.pop("url")
        headers = args.pop("headers", {})

        set_warnings(args.pop("error", None), args.pop("ignore", None))

        client = Client.open(url, headers=headers)
        set_conforms_to(
            client,
            args.pop("clear_conforms_to"),
            args.pop("remove_conforms_to", None),
            args.pop("add_conforms_to", None),
        )

        if cmd == "search":
            return search(client, **args)
        elif cmd == "collections":
            return collections(client, **args)
        else:
            logger.error(
                f"Command '{cmd}' is not a valid command. "
                "must be 'search' or 'collections'",
            )
            return 1
    except Exception as e:
        logger.error(e, exc_info=True)
        return 1


if __name__ == "__main__":
    return_code = cli()
    if return_code and return_code != 0:
        sys.exit(return_code)
