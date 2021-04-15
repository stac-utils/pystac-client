# flake8: noqa
from pystac import STAC_IO
import pystac.extensions.base

from pystac_client.version import __version__
from pystac_client.stac_api_object import STACAPIObjectMixin
from pystac_client.item_collection import ItemCollection
from pystac_client.extensions import APIExtensions
from pystac_client.item_search import ItemSearch
from pystac_client.client import Client
from pystac_client.conformance import ConformanceClasses

from pystac_client.stac_io import read_text_method

from pystac_client import extensions
import pystac_client.extensions.context

# Replace the read_text_method
STAC_IO.read_text_method = read_text_method

# Add API Extensions
STAC_API_EXTENSIONS = pystac.extensions.base.RegisteredSTACExtensions(
    [extensions.context.CONTEXT_EXTENSION_DEFINITION])
