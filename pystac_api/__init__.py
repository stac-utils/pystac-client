# flake8: noqa
import pystac

from pystac_api.version import __version__

from pystac_api.api import API
from pystac_api.conformance import ConformanceClasses

from pystac_api.stac_io import read_text_method

pystac.STAC_IO.read_text_method = read_text_method
