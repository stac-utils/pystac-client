# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import re
import subprocess
import sys
from pathlib import Path
from typing import List

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))
from pystac_client import __version__  # noqa: E402

git_branch = (
    subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    .decode("utf-8")
    .strip()
)

# -- Project information -----------------------------------------------------

project = "pystac-client"
copyright = "2021, Jon Duckworth"
author = "Matthew Hanson, Jon Duckworth"
github_user = "stac-utils"
github_repo = "pystac-client"
package_description = "A Python client for the STAC and STAC-API specs"

# The full version, including alpha/beta/rc tags
version = re.fullmatch(r"^(\d+\.\d+\.\d).*$", __version__).group(1)  # type: ignore
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.extlinks",
    "sphinxcontrib.fulltoc",
    "nbsphinx",
    "myst_parser",
]

extlinks = {
    "tutorial": (
        "https://github.com/stac-utils/pystac-client/"
        "tree/{}/docs/tutorials/%s".format(git_branch),
        "tutorial",
    )
}

nbsphinx_allow_errors = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
source_suffix = [".rst", "*.md", "*.ipynb"]
exclude_patterns = ["build/*"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/stac-utils/pystac-client",
            "icon": "fab fa-github-square",
        },
        {
            "name": "Gitter",
            "url": "https://gitter.im/SpatioTemporal-Asset-Catalog/"
            "python?utm_source=share-link&utm_medium=link&utm_campaign=share-link",
            "icon": "fab fa-gitter",
        },
    ],
    "external_links": [
        {"name": "STAC Spec", "url": "https://github.com/radiantearth/stac-spec"}
    ],
    "navigation_with_keys": False,
    # "navbar_end": ["navbar-icon-links.html", "search-field.html"]
}

html_logo = "_static/STAC-03.png"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path: List[str] = ["_static"]


# -- Options for intersphinx extension ---------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest", None),
    "pystac": ("https://pystac.readthedocs.io/en/latest", None),
    "dateutil": ("https://dateutil.readthedocs.io/en/stable/", None),
}

# -- Options for autodoc extension -------------------------------------------

autodoc_typehints = "none"
