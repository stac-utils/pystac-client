from urllib.parse import urlparse
from urllib.request import Request, urlopen


def read_text_method(request):
    """Overwrites the default method for reading text from a URL or file to allow :class:`urllib.request.Request`
    instances as input. This method also raises any :exc:`urllib.error.HTTPError` exceptions rather than catching
    them to allow us to handle different response status codes as needed."""
    use_http = isinstance(request, Request) or urlparse(request).scheme != ''
    if use_http:
        with urlopen(request) as f:
            return f.read().decode('utf-8')
    else:
        with open(request) as f:
            return f.read()
