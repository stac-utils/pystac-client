import typing
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from requests_mock.mocker import Mocker

from pystac_client.exceptions import APIError
from pystac_client.stac_api_io import StacApiIO

from .helpers import STAC_URLS


class TestSTAC_IOOverride:
    @pytest.mark.vcr
    def test_request_input(self) -> None:
        stac_api_io = StacApiIO()
        response = stac_api_io.read_text(STAC_URLS["PLANETARY-COMPUTER"])
        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_str_input(self) -> None:
        stac_api_io = StacApiIO()
        response = stac_api_io.read_text(STAC_URLS["PLANETARY-COMPUTER"])

        assert isinstance(response, str)

    @pytest.mark.vcr
    def test_http_error(self) -> None:
        stac_api_io = StacApiIO()
        # Attempt to access an authenticated endpoint
        with pytest.raises(APIError) as excinfo:
            stac_api_io.read_text(f"{STAC_URLS['MLHUB']}/search")

        assert isinstance(excinfo.value, APIError)

    def test_local_file(self, tmp_path: Path) -> None:
        stac_api_io = StacApiIO()
        test_file = tmp_path / "test.txt"
        with test_file.open("w") as dst:
            dst.write("Hi there!")

        response = stac_api_io.read_text(str(test_file))

        assert response == "Hi there!"

    def test_conformance_deprecated(self) -> None:
        with pytest.warns(FutureWarning, match="`conformance` option is deprecated"):
            stac_api_io = StacApiIO(conformance=[])
        assert not hasattr(stac_api_io, "conformance")

    def test_custom_headers(self, requests_mock: Mocker) -> None:
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

    def test_modifier(self, requests_mock: Mocker) -> None:
        """Verify the modifier is correctly called with a returned object."""
        header_name = "x-my-header"
        header_value = "Some Value"
        url = "https://some-url.com/some-file.json"

        def custom_modifier(request: typing.Any) -> typing.Union[typing.Any, None]:
            request.headers["x-pirate-name"] = "yellowbeard"
            return request

        stac_api_io = StacApiIO(
            headers={header_name: header_value}, request_modifier=custom_modifier
        )

        requests_mock.get(url, status_code=200, json={})

        stac_api_io.read_json(url)

        history = requests_mock.request_history
        assert len(history) == 1
        assert header_name in history[0].headers
        assert history[0].headers["x-pirate-name"] == "yellowbeard"

    def test_modifier_noreturn(self, requests_mock: Mocker) -> None:
        """Verify the modifier is correctly called when None is returned."""
        header_name = "x-my-header"
        header_value = "Some Value"
        url = "https://some-url.com/some-file.json"

        def custom_modifier(request: typing.Any) -> typing.Union[typing.Any, None]:
            request.headers["x-pirate-name"] = "yellowbeard"
            return None

        stac_api_io = StacApiIO(
            headers={header_name: header_value}, request_modifier=custom_modifier
        )

        requests_mock.get(url, status_code=200, json={})

        stac_api_io.read_json(url)

        history = requests_mock.request_history
        assert len(history) == 1
        assert header_name in history[0].headers
        assert history[0].headers["x-pirate-name"] == "yellowbeard"

    def test_custom_query_params(self, requests_mock: Mocker) -> None:
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

    def test_write(self, tmp_path: Path) -> None:
        stac_api_io = StacApiIO()
        test_file = tmp_path / "test.txt"
        stac_api_io.write_text_to_href(str(test_file), "Hi there!")
        with open(test_file) as file:
            data = file.read()
        assert data == "Hi there!"

    @pytest.mark.parametrize(
        ("attribute", "endpoint"),
        (("features", "search"), ("collections", "collections")),
    )
    def test_stop_on_empty_page(
        self, requests_mock: Mocker, attribute: str, endpoint: str
    ) -> None:
        url = f"https://pystac-client.test/{endpoint}"
        requests_mock.get(
            url,
            status_code=200,
            json={
                attribute: [{"foo": "bar"}],
                "links": [
                    {
                        "rel": "next",
                        "href": url + "?token=baz",
                    }
                ],
            },
        )
        requests_mock.get(
            url + "?token=baz",
            status_code=200,
            json={
                attribute: [],
                "links": [
                    {
                        "rel": "next",
                        "href": url + "?token=bam",
                    }
                ],
            },
        )
        requests_mock.get(
            url + "?token=bam",
            status_code=500,
        )
        stac_api_io = StacApiIO()
        pages = list(stac_api_io.get_pages(url))
        assert len(pages) == 1
        assert pages[0][attribute][0]["foo"] == "bar"

    @pytest.mark.parametrize(
        ("attribute", "endpoint"),
        (("features", "search"), ("collections", "collections")),
    )
    def test_stop_on_attributeless_page(
        self, requests_mock: Mocker, attribute: str, endpoint: str
    ) -> None:
        url = f"https://pystac-client.test/{endpoint}"
        requests_mock.get(
            url,
            status_code=200,
            json={
                attribute: [{"foo": "bar"}],
                "links": [
                    {
                        "rel": "next",
                        "href": url + "?token=baz",
                    }
                ],
            },
        )
        requests_mock.get(
            url + "?token=baz",
            status_code=200,
            json={
                "links": [
                    {
                        "rel": "next",
                        "href": url + "?token=bam",
                    }
                ],
            },
        )
        requests_mock.get(
            url + "?token=bam",
            status_code=500,
        )
        stac_api_io = StacApiIO()
        pages = list(stac_api_io.get_pages(url))
        assert len(pages) == 1
        assert pages[0][attribute][0]["foo"] == "bar"

    @pytest.mark.parametrize(
        ("attribute", "endpoint"),
        (("features", "search"), ("collections", "collections")),
    )
    def test_stop_on_first_empty_page(
        self, requests_mock: Mocker, attribute: str, endpoint: str
    ) -> None:
        url = f"https://pystac-client.test/{endpoint}"
        requests_mock.get(
            url,
            status_code=200,
            json={
                attribute: [],
                "links": [
                    {
                        "rel": "next",
                        "href": url + "?token=bam",
                    }
                ],
            },
        )
        requests_mock.get(url + "?token=bam", status_code=500)
        stac_api_io = StacApiIO()
        pages = list(stac_api_io.get_pages(url))
        assert len(pages) == 0

    @pytest.mark.vcr
    def test_timeout_smoke_test(self) -> None:
        # Testing timeout behavior is hard, so we just have a simple smoke test to make
        # sure that providing a timeout doesn't break anything.
        stac_api_io = StacApiIO(timeout=42)
        response = stac_api_io.read_text(STAC_URLS["PLANETARY-COMPUTER"])
        assert isinstance(response, str)
