import json
from pathlib import Path

TEST_DATA = Path(__file__).parent / 'data'

STAC_URLS = {
    "PLANETARY-COMPUTER": "https://planetarycomputer.microsoft.com/api/stac/v1",
    "EARTH-SEARCH": "https://earth-search.aws.element84.com/v0",
    "MLHUB": "https://api.radiant.earth/mlhub/v1",
}


def read_data_file(file_name: str, mode='r', parse_json=False):
    file_path = TEST_DATA / file_name
    with file_path.open(mode=mode) as src:
        if parse_json:
            return json.load(src)
        else:
            return src.read()
