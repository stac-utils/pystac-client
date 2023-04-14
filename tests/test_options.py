import pytest

from pystac_client.options import get_options, T_Keys, T_Values


@pytest.mark.parametrize(
    "key,value",
    [
        ("on_fallback_to_pystac", "ignore"),
        ("on_missing_link", "ignore"),
        ("on_does_not_conform_to", "warn"),
    ],
)
def test_default_options(key: T_Keys, value: T_Values) -> None:
    assert get_options()[key] == value
