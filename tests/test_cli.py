from typing import List

import pytest
from pytest_console_scripts import ScriptRunner

import pystac_client.cli
from tests.helpers import STAC_URLS


class TestCLI:
    @pytest.mark.vcr
    def test_item_search(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "search",
            STAC_URLS["PLANETARY-COMPUTER"],
            "-c",
            "naip",
            "--max-items",
            "20",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success

    @pytest.mark.parametrize(
        "headers,good_header_count",
        [
            (["kick=flip", "home=run"], 2),
            (["mad=pow"], 1),
            (["=no-var"], 0),
            (["no-val="], 0),
            (["good=header", "bad-header"], 1),
            (["header=value-with-three-=-signs-=", "plain=jane"], 2),
        ],
    )
    def test_headers(self, headers: List[str], good_header_count: int) -> None:
        args = [
            "search",
            STAC_URLS["PLANETARY-COMPUTER"],
            "-c",
            "naip",
            "--max-items",
            "20",
            "--headers",
        ] + headers
        pargs = pystac_client.cli.parse_args(args)
        assert len(pargs["headers"]) == good_header_count

    def test_no_arguments(self, script_runner: ScriptRunner) -> None:
        args = ["stac-client"]
        result = script_runner.run(*args, print_result=False)
        assert not result.success
        assert result.returncode == 1

    @pytest.mark.vcr
    @pytest.mark.script_launch_mode("subprocess")
    def test_non_conformant_raises_by_default(
        self, script_runner: ScriptRunner
    ) -> None:
        args = [
            "stac-client",
            "search",
            "https://earth-search.aws.element84.com/v0",
            "-c",
            "sentinel-s2-l2a-cogs",
            "--matched",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success is False
        assert "Server does not advertise any conformance classes" in result.stderr
        assert result.returncode == 1

    @pytest.mark.vcr
    @pytest.mark.filterwarnings("ignore::pystac_client.warnings.NoConformsTo")
    def test_non_conformant_can_be_fixed(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "search",
            "https://earth-search.aws.element84.com/v0",
            "-c",
            "sentinel-s2-l2a-cogs",
            "--add-conforms-to=ITEM_SEARCH",
            "--matched",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success
