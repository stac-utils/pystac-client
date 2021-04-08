STAC API Client
===============

A Python client for working with STAC APIs.

## Installation

```shell
pip install git+https://github.com/duckontheweb/pystac-api.git#egg=pystac_api
```

## Usage

Create an API instance for each STAC API

```
import pystac_api_client as stac

api = stac.API.open("https://earth-search.aws.element84.com/v0")
```

Create a search
```
mysearch = api.search(collections=['sentinel-s2-l2a-cogs'], bbox='')

print(mysearch.matched())
```

Iterate through items

```
for item in mysearch.items():
    print(item.id)
```

Save all found items as a single FeatureCollection

```
mysearch.save()
```


Save all found items in a local static catalog



## Development

Requires that you have [`poetry`](https://python-poetry.org/) installed

```shell
poetry install
```

### Build Docs

```shell
poetry run inv build-docs
```

### Run Tests

```shell
poetry run inv unit-tests --coverage
```

### Lint

```shell
poetry run inv lint
```

