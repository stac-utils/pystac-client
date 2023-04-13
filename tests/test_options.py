from pystac_client.options import get_options, set_options

def test_options():
    assert get_options("enforce_conformance") is True
    assert False