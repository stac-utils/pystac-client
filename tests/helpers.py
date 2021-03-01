import json
from pathlib import Path

ASTRAEA_URL = 'https://eod-catalog-svc-prod.astraea.earth'


def read_data_file(file_name: str, mode='r', parse_json=False):
    file_path = Path(__file__).parent / 'data' / file_name
    with file_path.open(mode=mode) as src:
        if parse_json:
            return json.load(src)
        else:
            return src.read()
