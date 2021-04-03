import logging
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def read_text_method(uri):
    """Overwrites the default method for reading text from a URL or file to allow :class:`urllib.request.Request`
    instances as input. This method also raises any :exc:`urllib.error.HTTPError` exceptions rather than catching
    them to allow us to handle different response status codes as needed."""
    if bool(urlparse(uri).scheme):
        logger.debug(f"Requesting {uri}")
        return requests.get(uri).content
    else:
        return STAC_IO.default_read_text_method(uri)