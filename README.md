STAC Client
===============

[![CI](https://github.com/stac-utils/pystac-client/actions/workflows/continuous-integration.yml/badge.svg)](https://github.com/stac-utils/pystac-client/actions/workflows/continuous-integration.yml)
[![Release](https://github.com/stac-utils/pystac-client/actions/workflows/release.yml/badge.svg)](https://github.com/stac-utils/pystac-client/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/pystac-client.svg)](https://badge.fury.io/py/pystac-client)
[![Documentation](https://readthedocs.org/projects/pystac-client/badge/?version=latest)](https://pystac-client.readthedocs.io/en/latest/)
[![codecov](https://codecov.io/gh/stac-utils/pystac-client/branch/main/graph/badge.svg)](https://codecov.io/gh/stac-utils/pystac-client)


A Python client for working with [STAC](https://stacspec.org/) Catalogs and APIs.

## Installation

Install from PyPi. Other than [PySTAC](https://pystac.readthedocs.io) itself, the only dependencies for pystac-client is the Python [requests](https://docs.python-requests.org) and [dateutil](https://dateutil.readthedocs.io) libraries.

```shell
$ pip install pystac-client
```

## Documentation

See the [documentation page](https://pystac-client.readthedocs.io/en/latest/) for the latest docs.

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
$ pytest -v -s --block-network --cov pystac_client --cov-report term-missing
```

The pystac-client tests use [vcrpy](https://vcrpy.readthedocs.io/en/latest/) to mock API calls
with "pre-recorded" API responses. When adding new tests use the `@pytest.mark.vcr` decorator
function to indicate `vcrpy` should be used. Record the new responses and commit them to the 
repository.

```shell
$ pytest -v -s --record-mode new_episodes --block-network
$ git add <new files here>
$ git commit -a -m 'new test episodes'
```

To update pystac-client to use future versions of STAC API, the existing recorded API responsees
should be "re-recorded":

```shell
$ pytest -v -s --record-mode rewrite --block-network
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

To build the documentation, install the documentation requirements, then use the `build-docs` script:

```shell
$ pip install -r requirements-docs.txt
$ scripts/build-docs
```
