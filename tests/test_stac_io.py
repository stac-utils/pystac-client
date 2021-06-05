from urllib.error import HTTPError
from urllib.request import Request

import pytest

from pystac_client.stac_io import StacApiIO

from .helpers import ASTRAEA_URL, MLHUB_URL


class TestSTAC_IOOverride:
    @pytest.mark.vcr
    def test_request_input(self):
        stac_api_io = StacApiIO()
        request = Request(url=ASTRAEA_URL)
        response = stac_api_io.read_text(request)

        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_str_input(self):
        stac_api_io = StacApiIO()
        response = stac_api_io.read_text(ASTRAEA_URL)

        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_http_error(self):
        stac_api_io = StacApiIO()
        # Attempt to access an authenticated endpoint
        request = Request(url=f'{MLHUB_URL}/search')
        with pytest.raises(HTTPError) as excinfo:
            stac_api_io.read_text(request)

        assert isinstance(excinfo.value, HTTPError)

    def test_local_file(self, tmp_path):
        stac_api_io = StacApiIO()
        test_file = tmp_path / 'test.txt'
        with test_file.open('w') as dst:
            dst.write('Hi there!')

        response = stac_api_io.read_text(str(test_file))

        assert response == 'Hi there!'
