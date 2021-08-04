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

## Quickstart

pystac-client can be used as either a Command Line Interface (CLI) or a Python library.

### CLI

Use the CLI to quickly make searches and output or save the results.

The `--matched` switch performs a search with limit=1 so does not get any Items, but gets the total number of matches which will be output to the screen (if supported by the STAC API).

```
$ stac-client search https://earth-search.aws.element84.com/v0 -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --matched
2179 items matched
```

If the same URL is to be used over and over, define an environment variable to be used in the CLI call:

```
$ export STAC_API_URL=https://earth-search.aws.element84.com/v0
$ stac-client search ${STAC_API_URL} -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 --matched
48 items matched
```

Without the `--matched` switch, all items will be fetched, paginating if necessary. If the `--max-items` switch 
is provided it will stop paging once that many items has been retrieved. It then prints all items to stdout as an 
ItemCollection. This can be useful to pipe output to another process such as [stac-terminal](https://github.com/stac-utils/stac-terminal), [geojsonio-cli](https://github.com/mapbox/geojsonio-cli), or [jq](https://stedolan.github.io/jq/).

```
$ stac-client search ${STAC_API_URL} -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 | stacterm cal --label platform
```

![](docs/source/images/stacterm-cal.png)

If the `--save` switch is provided instead, the results will not be output to stdout, but instead will be saved to
the specified file.

```
$ stac-client search ${STAC_API_URL} -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 --save items.json
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
$ stac-client search ${STAC_API_URL} -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 -q "eo:cloud_cover<10" --matched
10 items matched
```

```
stac-client search ${STAC_API_URL} -c sentinel-s2-l2a-cogs --bbox -72.5 40.5 -72 41 --datetime 2020-01-01/2020-01-31 -q "eo:cloud_cover<10" "eo:cloud_cover>5" --matched
```

### Python

To use the Python library, first a Client instance is created for a specific STAC API (use the root URL)

```
from pystac_client import Client

catalog = Client.open("https://earth-search.aws.element84.com/v0")
```

Create a search
```
mysearch = catalog.search(collections=['sentinel-s2-l2a-cogs'], bbox=[-72.5,40.5,-72,41], max_items=10)
print(f"{mysearch.matched()} items found")
```

The `get_items` function returns an iterator for looping through he returned items.

```
for item in mysearch.get_items():
    print(item.id)
```

To get all of Items from a search as a single
[PySTAC ItemCollection](https://pystac.readthedocs.io/en/latest/api.html#itemcollection)
use the `get_all_items` function. The `ItemCollection` can then be saved as a
GeoJSON FeatureCollection.

Save all found items as a single FeatureCollection

```
items = mysearch.get_all_items()
items.save('items.json')
```

## Development

For development, clone the repository and use the standard Python method for installing
the library as an "editable link", then install the development dependencies:

```shell
$ git clone https://github.com/stac-utils/pystac-client.git
$ cd pystac-client
$ pip install -e .
$ pip install -r requirements-dev.txt
```

To run just the tests

```shell
$ pytest -v -s --cov pystac_client --cov-report term-missing
```

The pystac-client tests use [vcrpy](https://vcrpy.readthedocs.io/en/latest/) to mock API calls
with "pre-recorded" API responses. When adding new tests use the `@pytest.mark.vcr` decorator
function to indicate `vcrpy` should be used. Record the new responses and commit them to the 
repository.

```shell
$ pytest -v -s --record-mode new_episodes
$ git add <new files here>
$ git commit -a -m 'new test episodes'
```

To update pystac-client to use future versions of STAC API, the existing recorded API responsees
should be "re-recorded":

```shell
$ pytest -v -s --record-mode rewrite
$ git commit -a -m 'updated test episodes'
```

### Pull Requests

To make Pull Requests to pystac-client, the code must pass linting, formatting, and code tests. To run 
the entire suit of checks and tests that will be run the GitHub Action Pipeline, use the `test` script.

```shell
$ scripts/test
```

If automatic formatting is desired (incorrect formatting will cause the GitHub Action to fail),
use the format script and commit the resulting files:

```shell
$ scripts/format
$ git commit -a -m 'formatting updates'
```

To build the documentation, use the `build-docs` script:

```shell
$ scripts/build-docs
```
