from pystac_client.options import get_options


def test_options():
    assert get_options()["on_missing_link"] == "ignore"
