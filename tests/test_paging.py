import json
from urllib.parse import urlencode, urljoin
from urllib.request import Request

import pytest

from pystac_api.paging import paginate, simple_stac_resolver

from .helpers import ASTRAEA_URL


class TestSimpleSTACResolver:

    @pytest.fixture(scope='function')
    def original_request(self):
        original_url = 'https://some-domain.com/path'
        original_headers = {
            'X-overwrite': 'original',
            'X-original': 'original'
        }

        return Request(
            url=original_url,
            method='GET',
            headers=original_headers
        )

    def test_simple_href(self, original_request):
        """If only an href is provided, this should keep the original headers, but replace the URL with the given
        href."""
        # Next link
        link = {
            'rel': 'next',
            'href': 'http://some-other-domain/another-path'
        }

        next_request = simple_stac_resolver(link=link, original_request=original_request)

        assert next_request.full_url == link['href']
        assert next_request.headers == original_request.headers

    def test_merge_headers(self, original_request):
        """Should merge headers from "next" link with original headers, with headers from "next" link
        taking precedence."""
        link = {
            'rel': 'next',
            'merge': True,
            'headers': {'X-overwrite': 'link', 'X-link': 'link'},
            'href': 'https://some-domain.com/path?next=sometoken'
        }

        next_request = simple_stac_resolver(link=link, original_request=original_request)

        assert next_request.headers == {
            'X-overwrite': 'link',
            'X-original': 'original',
            'X-link': 'link'
        }

    def test_overwrite_headers(self, original_request):
        """Should not preserve any of the original headers if "merge" is false and "headers" are present
        in the next link."""
        link = {
            'rel': 'next',
            'headers': {'X-overwrite': 'link', 'X-link': 'link'},
            'href': 'https://some-domain.com/path?next=sometoken'
        }

        next_request = simple_stac_resolver(link=link, original_request=original_request)

        assert next_request.headers == {
            'X-overwrite': 'link',
            'X-link': 'link'
        }

        # Should overwrite headers with empty dictionary as long as the attribute is present
        link = {
            'rel': 'next',
            'headers': {},
            'href': 'https://some-domain.com/path?next=sometoken'
        }

        next_request = simple_stac_resolver(link=link, original_request=original_request)

        assert next_request.headers == {}

    def test_get_to_post(self, original_request):
        link = {
            'rel': 'next',
            'body': {'param': 'link'},
            'href': 'https://some-domain.com/path?next=sometoken'
        }

        next_request = simple_stac_resolver(link=link, original_request=original_request)

        # This should be inferred from the fact that a "body" attribute is present.
        assert next_request.method == 'POST'
        assert json.loads(next_request.data.decode('utf-8')) == link['body']

    def test_merge_post(self, original_request):
        original_request.method = 'POST'
        original_request.data = json.dumps({
            'overwrite-param': 'from-original',
            'original-param': 'from-original'
        }).encode('utf-8')

        link = {
            'rel': 'next',
            'body': {'overwrite-param': 'from-link', 'link-param': 'from-link'},
            'href': 'https://some-domain.com/path?next=sometoken',
            'method': 'POST',
            'merge': True
        }

        next_request = simple_stac_resolver(link=link, original_request=original_request)

        next_body = json.loads(next_request.data.decode('utf-8'))

        assert next_request.method == 'POST'
        assert next_body == {
            'overwrite-param': 'from-link',
            'link-param': 'from-link',
            'original-param': 'from-original'
        }


class TestPaginate:

    @pytest.mark.vcr
    def test_paginate(self):
        params = {
            'datetime': '2019-01-01T00:00:01Z/2019-01-01T00:00:10Z',
            'limit': 10
        }
        original_request = Request(
            url='?'.join([urljoin(ASTRAEA_URL, 'search'), urlencode(params)]),
            method='GET'
        )

        pages = list(paginate(original_request, simple_stac_resolver))

        # This service returns a final page with 0 features before omitting the next link, so we end up
        # fetching 3 pages before breaking the loop
        assert len(pages) == 3
