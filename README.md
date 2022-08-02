# STAC Client <!-- omit in toc -->

[![CI](https://github.com/stac-utils/pystac-client/actions/workflows/continuous-integration.yml/badge.svg)](https://github.com/stac-utils/pystac-client/actions/workflows/continuous-integration.yml)
[![Release](https://github.com/stac-utils/pystac-client/actions/workflows/release.yml/badge.svg)](https://github.com/stac-utils/pystac-client/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/pystac-client.svg)](https://badge.fury.io/py/pystac-client)
[![Documentation](https://readthedocs.org/projects/pystac-client/badge/?version=latest)](https://pystac-client.readthedocs.io/en/latest/)
[![codecov](https://codecov.io/gh/stac-utils/pystac-client/branch/main/graph/badge.svg)](https://codecov.io/gh/stac-utils/pystac-client)


A Python client for working with [STAC](https://stacspec.org/) Catalogs and APIs.

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Installation](#installation)
- [Documentation](#documentation)
- [Development](#development)
  - [Pull Requests](#pull-requests)
  - [Benchmark](#benchmark)

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

[pre-commit](https://pre-commit.com/) is used to ensure a standard set of formatting and
linting is run before every commit. These hooks should be installed with:

```shell
$ pre-commit install
```

These can then be run independent of a commit with:

```shell
$ pre-commit run --all-files
```

To run just the tests:

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

To update pystac-client to use future versions of STAC API, the existing recorded API responses
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

To build the documentation, [install Pandoc](https://pandoc.org/installing.html), install the
Python documentation requirements via pip, then use the `build-docs` script:

```shell
$ pip install -r requirements-docs.txt
$ scripts/build-docs
```

### Benchmark

By default, pystac-client benchmarks are skipped during test runs.
To run the benchmarks, use the `--benchmark-only` flag:

```shell
$ pytest --benchmark-only
============================= test session starts ==============================
platform darwin -- Python 3.9.13, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
benchmark: 3.4.1 (defaults: timer=time.perf_counter disable_gc=False min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=100000)
rootdir: /Users/gadomski/Code/pystac-client, configfile: pytest.ini
plugins: benchmark-3.4.1, recording-0.11.0, console-scripts-1.1.0, requests-mock-1.9.3, cov-2.11.1, typeguard-2.13.3
collected 75 items

tests/test_cli.py ss                                                     [  2%]
tests/test_client.py ssssssssssssssss                                    [ 24%]
tests/test_collection_client.py ss                                       [ 26%]
tests/test_item_search.py ...sssssssssssssssssssssssssssssssssssssssssss [ 88%]
s                                                                        [ 89%]
tests/test_stac_api_io.py ssssssss                                       [100%]


--------------------------------------------------------------------------------------- benchmark: 3 tests --------------------------------------------------------------------------------------
Name (time in ms)                Min                 Max                Mean              StdDev              Median                IQR            Outliers     OPS            Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_single_item_search     213.4729 (1.0)      284.8732 (1.0)      254.9405 (1.0)       32.9424 (3.27)     271.0926 (1.0)      58.2907 (4.95)          1;0  3.9225 (1.0)           5           1
test_single_item            314.6746 (1.47)     679.7592 (2.39)     563.9692 (2.21)     142.7451 (14.18)    609.5605 (2.25)     93.9942 (7.98)          1;1  1.7731 (0.45)          5           1
test_requests               612.9212 (2.87)     640.5024 (2.25)     625.6871 (2.45)      10.0637 (1.0)      625.1143 (2.31)     11.7822 (1.0)           2;0  1.5982 (0.41)          5           1
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
======================== 3 passed, 72 skipped in 11.86s ========================
```

For more information on running and comparing benchmarks, see the [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/en/latest/).
