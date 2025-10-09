import pytest

from pystac_client.conformance import ConformanceClasses


class TestConformanceClasses:
    def test_get_by_name_raises_for_invalid_names(self) -> None:
        """Test get_by_name raises ValueError for invalid conformance class names."""
        with pytest.raises(ValueError, match="Invalid conformance class 'invalid'"):
            ConformanceClasses.get_by_name("invalid")

        with pytest.raises(ValueError, match="Invalid conformance class 'nonexistent'"):
            ConformanceClasses.get_by_name("nonexistent")

        with pytest.raises(ValueError, match="Invalid conformance class ''"):
            ConformanceClasses.get_by_name("")

    def test_get_by_name_valid(self) -> None:
        """Test get_by_name with valid conformance class names."""
        assert ConformanceClasses.get_by_name("core") == ConformanceClasses.CORE
        assert ConformanceClasses.get_by_name("CORE") == ConformanceClasses.CORE

    def test_valid_uri_property(self) -> None:
        """Test valid_uri property returns correct URI pattern."""
        assert (
            ConformanceClasses.CORE.valid_uri == "https://api.stacspec.org/v1.0.*/core"
        )

    def test_pattern_property(self) -> None:
        """Test pattern property returns compiled regex."""
        core_pattern = ConformanceClasses.CORE.pattern
        assert core_pattern.match("https://api.stacspec.org/v1.0.0/core")
