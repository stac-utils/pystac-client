import json
from pathlib import Path

ASTRAEA_URL = 'https://eod-catalog-svc-prod.astraea.earth'
MLHUB_URL = 'https://api.radiant.earth/mlhub/v1/'

TEST_DATA = Path(__file__).parent / 'data'


def read_data_file(file_name: str, mode='r', parse_json=False):
    file_path = TEST_DATA / file_name
    with file_path.open(mode=mode) as src:
        if parse_json:
            return json.load(src)
        else:
            return src.read()


ASTRAEA_API_PATH = str(TEST_DATA / 'astraea_api.json')
