# flake8: noqa
from pystac import STAC_IO
import pystac.extensions.base

from pystac_api.version import __version__
from pystac_api.stac_api_object import STACAPIObjectMixin
from pystac_api.item_collection import ItemCollection
from pystac_api.extensions import APIExtensions
from pystac_api.item_search import ItemSearch
from pystac_api.api import API
from pystac_api.conformance import ConformanceClasses

from pystac_api.stac_io import read_text_method

from pystac_api import extensions
import pystac_api.extensions.context

# Replace the read_text_method
STAC_IO.read_text_method = read_text_method

# Add API Extensions
STAC_API_EXTENSIONS = pystac.extensions.base.RegisteredSTACExtensions(
    [extensions.context.CONTEXT_EXTENSION_DEFINITION])
