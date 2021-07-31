STAC API Client
===============

[![CI](https://github.com/stac-utils/pystac-client/actions/workflows/continuous-integration.yml/badge.svg)](https://github.com/stac-utils/pystac-client/actions/workflows/continuous-integration.yml)
[![Release](https://github.com/stac-utils/pystac-client/actions/workflows/release.yml/badge.svg)](https://github.com/stac-utils/pystac-client/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/pystac-client.svg)](https://badge.fury.io/py/pystac-client)
[![Documentation](https://readthedocs.org/projects/pystac-client/badge/?version=latest)](https://pystac-client.readthedocs.io/en/latest/)
[![codecov](https://codecov.io/gh/stac-utils/pystac-client/branch/main/graph/badge.svg)](https://codecov.io/gh/stac-utils/pystac-client)


A Python client for working with [STAC](https://stacspec.org/) Catalogs and APIs.

## Installation

Install from PyPi. Other than PySTAC itself, the only dependency for pystac-client is the Python `requests` library.

```shell
pip install pystac-client
```

## Documentation

See the [documentation page](https://pystac-client.readthedocs.io/en/latest/) for the latest docs.

## Usage

pystac-client can be used as either a CLI or a Python library.

### CLI

Use the CLI to quickly make searches and output or save the results.

```
$ stac-client search --url https://earth-search.aws.element84.com/v0 -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41
1999 items matched
```

The `--matched` switch performs a search with limit=0 so does not get any Items, but gets the total number of 
matches which will be output to the screen.

The environment variable `STAC_URL` can be set instead of having to explicitly set the Catalog URL with every call:

```
$ export STAC_URL=https://earth-search.aws.element84.com/v0 
$ stac-client search -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 --matched
48 items matched
```

Without the `--matched` switch, all items will be fetched, paginating if necessary. If `max_items` is provided 
it will stop paging once that many items has been retrieved. It then prints all items to stdout as an ItemCollection.
This can be useful to pipe output to another process such as [stac-terminal](https://github.com/stac-utils/stac-terminal),
[geojsonio-cli](https://github.com/mapbox/geojsonio-cli), or [jq](https://stedolan.github.io/jq/).

```
$ stac-client search -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 | stacterm cal --label platform
```

![](docs/source/images/stacterm-cal.png)

If the `--save` switch is provided instead, the results will not be output to stdout, but instead will be saved to
the specified file.

```
$ stac-client search -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 --save items.json
```

If the Catalog supports the [Query extension](https://github.com/radiantearth/stac-api-spec/tree/master/fragments/query),
any Item property can also be included in the search. Rather than requiring the JSON syntax the Query extension uses,
pystac-client uses a simpler syntax that it will translate to the JSON equivalent. 

```
<property><operator><value>

where operator is one of `>=`, `<=`, `>`, `<`, `=`

Examples:
eo:cloud_cover<10
created=2021-01-06
view:sun_elevation<20
```


Any number of properties can be included, and each can be included more than once to use additional operators.

```
$ stac-client search -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 -q "eo:cloud_cover<10" --matched
10 items matched
```

### Python

To use the Python library, first an API instance is created for a specific STAC API (use the root URL)

```
from pystac_client import Client

catalog = Client.open("https://earth-search.aws.element84.com/v0")
```

Create a search
```
mysearch = catalog.search(collections=['sentinel-s2-l2a-cogs'], bbox=[-72.5,40.5,-72,41], max_items=10)
print(f"{mysearch.matched()} items found")
```

Iterate through items

```
for item in mysearch.items():
    print(item.id)
```

Save all found items as a single FeatureCollection

```
items = mysearch.items_as_collection()
items.save('items.json')
```

## Development

### Install

```shell
$ pip install -e .
$ pip install -r requirements-dev.txt
```

### Build Docs

```shell
$ scripts/build-docs
```

### Run Tests

```shell
$ scripts/test
```

or

```shell
$ pytest -v -s --cov pystac_client --cov-report term-missing
```

### Lint

```shell
$ scripts/format
```

