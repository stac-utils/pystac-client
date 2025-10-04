import typing
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pystac
import pytest
from pytest import MonkeyPatch
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

        def custom_modifier(request: typing.Any) -> typing.Any | None:
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

        def custom_modifier(request: typing.Any) -> typing.Any | None:
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

    @pytest.mark.parametrize("name", ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"))
    def test_respect_env_for_certs(self, monkeypatch: MonkeyPatch, name: str) -> None:
        monkeypatch.setenv(name, "/not/a/real/file")
        stac_api_io = StacApiIO()
        with pytest.raises(APIError):
            stac_api_io.request("https://earth-search.aws.element84.com/v1/")


@pytest.mark.vcr
def test_stac_io_in_pystac() -> None:
    # https://github.com/stac-utils/pystac-client/issues/706
    collection = pystac.read_file(
        href="tests/data/planetary-computer-collection.json",
        stac_io=StacApiIO(timeout=42),
    )
    root = collection.get_root()
    assert root
    stac_io = root._stac_io
    assert isinstance(stac_io, StacApiIO)
    assert stac_io.timeout == 42


def test_request_decode_error(requests_mock: Mocker) -> None:
    """Test that decode errors in request() are properly handled."""
    url = "https://example.com/bad-encoding"
    # Mock a response with invalid UTF-8 content
    requests_mock.get(url, status_code=200, content=b"\xff\xfe\x00\x00")

    stac_api_io = StacApiIO()

    with pytest.raises(APIError) as excinfo:
        stac_api_io.request(url)

    assert (
        "decode" in str(excinfo.value).lower() or "utf-8" in str(excinfo.value).lower()
    )


def test_write_text_to_href_url_error() -> None:
    """Test that write_text_to_href raises APIError for URLs."""
    stac_api_io = StacApiIO()

    with pytest.raises(APIError, match="Transactions not supported"):
        stac_api_io.write_text_to_href("https://example.com/write", "content")


def test_stac_object_from_dict_unknown_type(monkeypatch: MonkeyPatch) -> None:
    """Test that unknown STAC object types raise ValueError."""
    stac_api_io = StacApiIO()

    import json

    with open("tests/data/planetary-computer-collection.json") as f:
        real_stac_data = json.load(f)

    # Mock identify_stac_object to return an unknown type
    class MockInfo:
        object_type = "UNKNOWN_TYPE"

    def mock_identify_stac_object(d: dict[str, Any]) -> MockInfo:
        return MockInfo()

    # Mock migrate_to_latest to just return the data unchanged
    def mock_migrate_to_latest(d: dict[str, Any], info: MockInfo) -> dict[str, Any]:
        return d

    monkeypatch.setattr(
        "pystac_client.stac_api_io.identify_stac_object", mock_identify_stac_object
    )
    monkeypatch.setattr(
        "pystac_client.stac_api_io.migrate_to_latest", mock_migrate_to_latest
    )

    with pytest.raises(ValueError, match="Unknown STAC object type"):
        stac_api_io.stac_object_from_dict(real_stac_data)
