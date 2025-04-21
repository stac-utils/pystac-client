PySTAC Client Documentation
===========================

PySTAC Client is a Python package for working with `STAC <https://github.com/radiantearth/stac-spec>`__
Catalogs and `STAC APIs <https://github.com/radiantearth/stac-api-spec>`__.
PySTAC Client builds upon PySTAC through higher-level functionality and ability to
access STAC API search endpoints.

STAC Versions
=============

+---------------+-----------+-----------------------------+
| pystac-client | STAC spec | STAC API Spec               |
+===============+===========+=============================+
| 0.8.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0        |
+---------------+-----------+-----------------------------+
| 0.7.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0        |
+---------------+-----------+-----------------------------+
| 0.6.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-rc.2   |
+---------------+-----------+-----------------------------+
| 0.5.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-rc.1   |
+---------------+-----------+-----------------------------+
| 0.4.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-rc.1   |
+---------------+-----------+-----------------------------+
| 0.3.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-beta.4 |
+---------------+-----------+-----------------------------+
| 0.2.x         | 1.0.x     | 1.0.0-beta.1 - 1.0.0-beta.2 |
+---------------+-----------+-----------------------------+

Installation
------------

``pystac-client`` requires `Python >=3.10 <https://www.python.org/>`__.

pip:

.. code-block:: console

   $ pip install pystac-client

uv:

.. code-block:: console

   $ uv add pystac-client

poetry:

.. code-block:: console

   $ poetry add pystac-client


This will install the dependencies :doc:`pystac <pystac:index>`,
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
