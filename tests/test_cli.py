import pytest
from pytest_console_scripts import ScriptRunner

from tests.helpers import ASTRAEA_URL


class TestCLI:
    @pytest.mark.vcr
    def test_item_search(self, script_runner: ScriptRunner):
        args = ["stac-client", "search", "--url", ASTRAEA_URL, "-c", "naip", "--max-items", "20"]
        result = script_runner.run(*args, print_result=False)
        assert result.success
