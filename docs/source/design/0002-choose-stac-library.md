# 2. Choose STAC library

Date: 2021-03-01

## Status

Accepted

## Context

We would like to use an existing Python library for working with STAC objects as Python objects. Ideally this library 
will meet the following requirements:

* **Actively maintained** to ensure that it is up-to-date with the latest STAC spec
* **Well-documented** to reduce the documentation burden for this library
* **Easily extensible** to allow us to take advantage of existing STAC object functionality

The 2 most obvious choices for Python STAC clients are 
[`PySTAC`](https://github.com/stac-utils/pystac) and [`sat-stac`](https://github.com/sat-utils/sat-stac). 

### `PySTAC`

`PySTAC` is an actively maintained STAC client for Python 3. Its last release was less than 2 months ago and its last 
commit was less than 2 weeks ago. It has had 15 contributors within the last year and it supports the latest release 
candidate for the STAC spec (as well as previous releases). `PySTAC` hosts 
[documentation on ReadTheDocs](https://pystac.readthedocs.io/en/latest/) that includes a description of programming 
concepts related to the library, quickstart instructions, tutorials, and an API reference.

`PySTAC` supports both reading and writing of STAC objects. Extending `PySTAC` classes through inheritance is made a 
bit more difficult by the fact that some class methods (like ``from_dict``) have references to specific classes 
(like ``Catalog``) rather than using the ``cls`` argument. This will require us to overwrite some of these methods to 
implement inheritance. It has robust support for traversing catalogs using links. There is no existing support for the 
STAC API spec in `PySTAC` or any related tooling.

### `sat-stac`

`sat-stac` is an actively maintained STAC client for Python 3. Its last release was less than 2 months ago and its 
last commit was at that same time. It has had 2 contributors within the last year and it supports the latest release 
candidate for the STAC spec (as well as previous releases). `sat-stac` has installation documented in the GitHub repo's 
main README and has 2 tutorials in the form of Jupyter Notebooks in that repo. 

`sat-stac` supports reading STAC catalogs (support for writing STAC catalogs was removed in v0.4.0). There is also an 
existing library for working with STAC API - Item Search results called 
[sat-search](https://github.com/sat-utils/sat-search) that uses `sat-stac` as its backend. 

## Decision

We will use `PySTAC` as our "backend" for working with STAC objects in Python. While both libraries are well-maintained, 
`PySTAC` has more thorough documentation and seems to be more widely supported through community contribution. 

## Consequences

We will need to create our own implementation of a STAC API - Item Search client since there is not existing tooling 
based on `PySTAC`. We will be able to point to the hosted documentation for `PySTAC` to guide users through existing 
functionality for navigating STAC Catalogs. Special care should be taken to ensure that we do not break any of 
`PySTAC`'s functionality through inheritance.
