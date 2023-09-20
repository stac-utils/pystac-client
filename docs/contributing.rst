Contributing
============

A list of issues and ongoing work is available on the PySTAC Client `issues page
<https://github.com/stac-utils/pystac-client/issues>`_. If you want to contribute code, the best
way is to coordinate with the core developers via an issue or pull request conversation.

Development installation
^^^^^^^^^^^^^^^^^^^^^^^^
Fork PySTAC Client into your GitHub account. Clone the repo, install
the library as an "editable link", then install the development dependencies:

.. code-block:: bash

    $ git clone git@github.com:your_user_name/pystac-client.git
    $ cd pystac-client
    $ pip install -e '.[dev]'

Testing
^^^^^^^
tl;dr: Run ``./scripts/test`` to run all tests and linters.

PySTAC Client runs tests using `pytest <https://docs.pytest.org/en/latest/>`_. You can find unit tests in the ``tests/``
directory.

To run the tests and generate the coverage report:

.. code-block:: bash

    $ pytest -v -s --block-network --cov pystac_client --cov-report term-missing

The PySTAC Client tests use `vcrpy <https://vcrpy.readthedocs.io/en/latest/>`_ to mock API calls
with "pre-recorded" API responses. When adding new tests use the ``@pytest.mark.vcr`` decorator
function to indicate ``vcrpy`` should be used. Record the new responses and commit them to the
repository.

.. code-block:: bash

    $ pytest -v -s --record-mode new_episodes
    $ git add <new files here>
    $ git commit -a -m 'new test episodes'


To update PySTAC Client to use future versions of STAC API, the existing recorded API responses
should be "re-recorded":

.. code-block:: bash

    $ pytest -v -s --record-mode rewrite --block-network
    $ git commit -a -m 'updated test episodes'


Code quality checks
^^^^^^^^^^^^^^^^^^^

`pre-commit <https://pre-commit.com/>`_ is used to ensure a standard set of formatting and
linting is run before every commit. These hooks should be installed with:

.. code-block:: bash

    $ pre-commit install

These can then be run independent of a commit with:

.. code-block:: bash

    $ pre-commit run --all-files

PySTAC Client uses

- `black <https://github.com/psf/black>`_ for Python code formatting
- `codespell <https://github.com/codespell-project/codespell/>`_ to check code for common misspellings
- `doc8 <https://github.com/pycqa/doc8>`_ for style checking on RST files in the docs
- `ruff <https://beta.ruff.rs/docs/>`_ for Python style checks
- `mypy <http://www.mypy-lang.org/>`_ for Python type annotation checks

Once installed you can bypass pre-commit by adding the ``--no-verify`` (or ``-n``)
flag to Git commit commands, as in ``git commit --no-verify``.

Pull Requests
^^^^^^^^^^^^^

To make Pull Requests to PySTAC Client, the code must pass linting, formatting, and code tests. To run
the entire suit of checks and tests that will be run the GitHub Action Pipeline, use the ``test`` script.

.. code-block:: bash

    $ scripts/test

If automatic formatting is desired (incorrect formatting will cause the GitHub Action to fail),
use the format script and commit the resulting files:

.. code-block:: bash

    $ scripts/format
    $ git commit -a -m 'formatting updates'


To build the documentation, `install Pandoc <https://pandoc.org/installing.html>`_, install the
Python documentation requirements via pip, then use the ``build-docs`` script:

.. code-block:: bash

    $ pip install -e '.[docs]'
    $ scripts/build-docs

CHANGELOG
^^^^^^^^^

PySTAC Client maintains a
`changelog  <https://github.com/stac-utils/pystac-client/blob/main/CHANGELOG.md>`_
to track changes between releases. All Pull Requests should make a changelog entry unless
the change is trivial (e.g. fixing typos) or is entirely invisible to users who may
be upgrading versions (e.g. an improvement to the CI system).

For changelog entries, please link to the PR of that change. This needs to happen in a
few steps:

- Make a Pull Request (see above) to PySTAC Client with your changes
- Record the link to the Pull Request
- Push an additional commit to your branch with the changelog entry with the link to the
  Pull Request.

For more information on changelogs and how to write a good entry, see `keep a changelog
<https://keepachangelog.com/en/1.0.0/>`_.

Benchmark
^^^^^^^^^

By default, PySTAC Client benchmarks are skipped during test runs.
To run the benchmarks, use the ``--benchmark-only`` flag:

.. code-block:: bash

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


For more information on running and comparing benchmarks, see the `pytest-benchmark documentation <https://pytest-benchmark.readthedocs.io/en/latest/>`_.
