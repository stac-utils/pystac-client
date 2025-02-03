import json
import tempfile

import pytest
from pytest_console_scripts import ScriptRunner

import pystac_client.cli
from tests.helpers import STAC_URLS, TEST_DATA

FILTER_JSON = {"op": "lte", "args": [{"property": "eo:cloud_cover"}, 40]}


# We want to ensure that the CLI is handling these warnings properly
@pytest.mark.filterwarnings("ignore::pystac_client.warnings.PystacClientWarning")
class TestCLISearch:
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

    @pytest.mark.vcr
    def test_filter(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "search",
            STAC_URLS["EARTH-SEARCH"],
            "--filter",
            json.dumps(FILTER_JSON),
            "--max-items",
            "20",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success, result.stderr
        assert result.stdout

    @pytest.mark.vcr
    @pytest.mark.parametrize("filename", ["netherlands_aoi.json", "sample-item.json"])
    def test_intersects(self, script_runner: ScriptRunner, filename: str) -> None:
        args = [
            "stac-client",
            "search",
            STAC_URLS["PLANETARY-COMPUTER"],
            "--collections",
            "landsat-8-c2-l2",
            "--intersects",
            str(TEST_DATA / filename),
            "--max-items",
            "10",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success, result.stderr
        assert result.stdout

    @pytest.mark.vcr
    def test_intersects_despite_warning(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "search",
            STAC_URLS["PLANETARY-COMPUTER"],
            "--collections",
            "landsat-8-c2-l2",
            "--intersects",
            str(TEST_DATA / "sample-item-collection.json"),
            "--max-items",
            "10",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success
        assert result.stdout
        assert "input to intersects is a FeatureCollection" in result.stderr

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
    def test_headers(self, headers: list[str], good_header_count: int) -> None:
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
        assert "Server does not conform to ITEM_SEARCH" in result.stderr
        assert result.returncode == 1

    @pytest.mark.vcr
    @pytest.mark.parametrize("warning_flag", ["--error", "--error=no-conforms-to"])
    def test_non_conformant_raises_if_warning_set_to_error(
        self, script_runner: ScriptRunner, warning_flag: str
    ) -> None:
        args = [
            "stac-client",
            "search",
            "https://earth-search.aws.element84.com/v0",
            "-c",
            "sentinel-s2-l2a-cogs",
            warning_flag,
            "--matched",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success is False
        assert "Server does not advertise any conformance classes" in result.stderr
        assert result.returncode == 1

    @pytest.mark.vcr
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

    @pytest.mark.vcr
    @pytest.mark.parametrize("warning_flag", ["--ignore", "--ignore=no-conforms-to"])
    def test_non_conformant_can_be_ignored(
        self, script_runner: ScriptRunner, warning_flag: str
    ) -> None:
        args = [
            "stac-client",
            "search",
            "https://earth-search.aws.element84.com/v0",
            "-c",
            "sentinel-s2-l2a-cogs",
            warning_flag,
            "--add-conforms-to=ITEM_SEARCH",
            "--matched",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success

    @pytest.mark.vcr
    @pytest.mark.parametrize(
        "conforms_to_flag", ["--clear-conforms-to", "--remove-conforms-to=ITEM_SEARCH"]
    )
    def test_altering_conforms_to(
        self, script_runner: ScriptRunner, conforms_to_flag: str
    ) -> None:
        args = [
            "stac-client",
            "search",
            STAC_URLS["EARTH-SEARCH"],
            conforms_to_flag,
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success is False
        assert "Server does not conform to ITEM_SEARCH" in result.stderr
        assert result.returncode == 1

    @pytest.mark.vcr
    @pytest.mark.filterwarnings("ignore::Warning")
    def test_matched_not_available(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "search",
            STAC_URLS["PLANETARY-COMPUTER"],
            "-c",
            "naip",
            "--matched",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success is False
        assert "'matched' is not supported for this catalog" in result.stderr
        assert result.returncode == 1

    @pytest.mark.vcr
    def test_matched(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "search",
            STAC_URLS["EARTH-SEARCH"],
            "-c",
            "cop-dem-glo-30",
            "--max-items",
            "1",
            "--matched",
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success
        assert result.stdout[0].isdigit(), "Output does not start with a number"

    @pytest.mark.vcr
    def test_save(self, script_runner: ScriptRunner) -> None:
        with tempfile.NamedTemporaryFile() as fp:
            path = fp.name
        args = [
            "stac-client",
            "search",
            STAC_URLS["EARTH-SEARCH"],
            "-c",
            "cop-dem-glo-30",
            "--max-items",
            "1",
            "--save",
            path,
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success

        with open(path) as f:
            output = json.loads(f.read())

        assert "features" in output
        assert len(output["features"]) == 1


@pytest.mark.filterwarnings("ignore::pystac_client.warnings.PystacClientWarning")
class TestCLICollections:
    @pytest.mark.vcr
    def test_collections(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "collections",
            STAC_URLS["EARTH-SEARCH"],
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success
        assert result.stdout.startswith('[{"type": "Collection"')

    @pytest.mark.vcr
    def test_collection_search(self, script_runner: ScriptRunner) -> None:
        args = [
            "stac-client",
            "collections",
            STAC_URLS["EARTH-SEARCH"],
            "--q",
            "sentinel",
        ]
        with pytest.warns(UserWarning, match="COLLECTION_SEARCH"):
            result = script_runner.run(args, print_result=False)

        assert result.success

        collections = json.loads(result.stdout)
        assert len(collections) == 5

    @pytest.mark.vcr
    def test_save(self, script_runner: ScriptRunner) -> None:
        with tempfile.NamedTemporaryFile() as fp:
            path = fp.name
        args = [
            "stac-client",
            "collections",
            STAC_URLS["EARTH-SEARCH"],
            "--save",
            path,
        ]
        result = script_runner.run(args, print_result=False)
        assert result.success

        with open(path) as f:
            output = json.loads(f.read())

        assert isinstance(output, list)
        assert len(output) == 9, "earth-search does not have 9 collections"
        assert all(c["type"] == "Collection" for c in output)
