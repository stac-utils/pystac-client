from urllib.parse import parse_qs, urlsplit

import pytest
from pystac_client.conformance import ConformanceClasses

from pystac_client.exceptions import APIError
from pystac_client.stac_api_io import StacApiIO
from .helpers import STAC_URLS


class TestSTAC_IOOverride:
    @pytest.mark.vcr
    def test_request_input(self):
        stac_api_io = StacApiIO()
        response = stac_api_io.read_text(STAC_URLS['PLANETARY-COMPUTER'])
        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_str_input(self):
        stac_api_io = StacApiIO()
        response = stac_api_io.read_text(STAC_URLS['PLANETARY-COMPUTER'])

        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_http_error(self):
        stac_api_io = StacApiIO()
        # Attempt to access an authenticated endpoint
        with pytest.raises(APIError) as excinfo:
            stac_api_io.read_text(f"{STAC_URLS['MLHUB']}/search")

        assert isinstance(excinfo.value, APIError)

    def test_local_file(self, tmp_path):
        stac_api_io = StacApiIO()
        test_file = tmp_path / 'test.txt'
        with test_file.open('w') as dst:
            dst.write('Hi there!')

        response = stac_api_io.read_text(str(test_file))

        assert response == 'Hi there!'

    def test_assert_conforms_to(self):
        nonconformant = StacApiIO(conformance=[])

        with pytest.raises(NotImplementedError):
            nonconformant.assert_conforms_to(ConformanceClasses.CORE)

        conformant_io = StacApiIO(conformance=["https://api.stacspec.org/v1.0.0-beta.1/core"])

        # Check that this does not raise an exception
        conformant_io.assert_conforms_to(ConformanceClasses.CORE)

    def test_conforms_to(self):
        nonconformant = StacApiIO(conformance=[])

        assert not nonconformant.conforms_to(ConformanceClasses.CORE)

        conformant_io = StacApiIO(conformance=["https://api.stacspec.org/v1.0.0-beta.1/core"])

        # Check that this does not raise an exception
        assert conformant_io.conforms_to(ConformanceClasses.CORE)

    def test_custom_headers(self, requests_mock):
        """Checks that headers passed to the init method are added to requests."""
        header_name = "x-my-header"
        header_value = "Some Value"
        url = "https://some-url.com/some-file.json"
        stac_api_io = StacApiIO(headers={header_name: header_value})

        requests_mock.get(url, status_code=200, json={})

        stac_api_io.read_json(url)

        history = requests_mock.request_history
        assert len(history) == 1
        assert header_name in history[0].headers
        assert history[0].headers[header_name] == header_value

    def test_custom_query_params(self, requests_mock):
        """Checks that query params passed to the init method are added to requests."""
        init_qp_name = "my-param"
        init_qp_value = "something"
        url = "https://some-url.com/some-file.json"
        stac_api_io = StacApiIO(parameters={init_qp_name: init_qp_value})

        request_qp_name = "another-param"
        request_qp_value = "another_value"
        requests_mock.get(url, status_code=200, json={})

        stac_api_io.read_json(url, parameters={request_qp_name: request_qp_value})

        history = requests_mock.request_history
        assert len(history) == 1

        actual_qs = urlsplit(history[0].url).query
        actual_qp = parse_qs(actual_qs)

        # Check that the param from the init method is present
        assert init_qp_name in actual_qp
        assert len(actual_qp[init_qp_name]) == 1
        assert actual_qp[init_qp_name][0] == init_qp_value

        # Check that the param from the request is present
        assert request_qp_name in actual_qp
        assert len(actual_qp[request_qp_name]) == 1
        assert actual_qp[request_qp_name][0] == request_qp_value
