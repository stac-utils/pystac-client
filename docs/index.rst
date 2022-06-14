.. pystac-client documentation master file, created by
   sphinx-quickstart on Sat Feb 27 14:27:12 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PySTAC Client Documentation
===========================

The STAC Python Client (``pystac_client``) is a Python package for working with STAC
Catalogs and APIs that conform to the
`STAC <https://github.com/radiantearth/stac-spec>`__ and
`STAC API <https://github.com/radiantearth/stac-api-spec>`__ specs in a seamless way.
PySTAC Client builds upon PySTAC through higher-level functionality and ability to
leverage STAC API search endpoints.

STAC Versions
=============

+---------------+-----------+-----------------------------+
| pystac-client | STAC spec | STAC API Spec               |
+===============+===========+=============================+
| 0.4.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-rc.1   |
+---------------+-----------+-----------------------------+
| 0.3.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-beta.4 |
+---------------+-----------+-----------------------------+
| 0.2.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-beta.2 |
+---------------+-----------+-----------------------------+

Installation
------------

.. code-block:: console

   $ pip install pystac-client

``pystac_client`` requires `Python >=3.7 <https://www.python.org/>`__.

This will install the dependencies :doc:`PySTAC <pystac:index>`,
:doc:`python-dateutil <dateutil:index>`, and :doc:`requests <requests:index>`.

Acknowledgements
----------------

This package builds upon the great work of the PySTAC library for working with
STAC objects in Python. It also uses concepts from the
`sat-search <https://github.com/sat-utils/sat-search>`__ library for working with STAC
API search endpoints.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   quickstart
   usage
   api
   tutorials
   contributing
   design/design_decisions
