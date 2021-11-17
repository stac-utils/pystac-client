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
