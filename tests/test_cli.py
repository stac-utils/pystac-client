import pytest
from pytest_console_scripts import ScriptRunner

from tests.helpers import STAC_URLS


class TestCLI:
    @pytest.mark.vcr
    def test_item_search(self, script_runner: ScriptRunner):
        args = [
            "stac-client", "search", STAC_URLS['PLANETARY-COMPUTER'], "-c", "naip", "--max-items",
            "20"
        ]
        result = script_runner.run(*args, print_result=False)
        assert result.success

    def test_no_arguments(self, script_runner: ScriptRunner):
        args = ["stac-client"]
        result = script_runner.run(*args, print_result=False)
        assert result.success
