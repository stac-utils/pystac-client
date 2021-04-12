from urllib.error import HTTPError
from urllib.request import Request

import pytest

from pystac_client.stac_io import read_text_method

from .helpers import ASTRAEA_URL, MLHUB_URL


class TestSTAC_IOOverride:
    @pytest.mark.vcr
    def test_request_input(self):
        request = Request(url=ASTRAEA_URL)
        response = read_text_method(request)

        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_str_input(self):
        response = read_text_method(ASTRAEA_URL)

        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_http_error(self):
        # Attempt to access an authenticated endpoint
        request = Request(url=f'{MLHUB_URL}/search')
        with pytest.raises(HTTPError) as excinfo:
            read_text_method(request)

        assert isinstance(excinfo.value, HTTPError)

    def test_local_file(self, tmp_path):
        test_file = tmp_path / 'test.txt'
        with test_file.open('w') as dst:
            dst.write('Hi there!')

        response = read_text_method(str(test_file))

        assert response == 'Hi there!'
