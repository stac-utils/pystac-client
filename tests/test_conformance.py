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

    @pytest.mark.parametrize(
        "conformance_class, uri",
        [
            (ConformanceClasses.CORE, "v1.0.0-rc.1/core"),
            (ConformanceClasses.COLLECTIONS, "v1.0.0/collections"),
            (
                ConformanceClasses.COLLECTION_TRANSACTION,
                "v1.0.0/collections/extensions/transaction",
            ),
            (
                ConformanceClasses.TRANSACTION,
                "v1.0.0/ogcapi-features/extensions/transaction",
            ),
            (ConformanceClasses.FILTER, "v1.0.0-rc.2/item-search#filter"),
            (
                ConformanceClasses.FILTER,
                "v1.0.0-beta.4/item-search#filter:item-search-filter",
            ),
            (ConformanceClasses.ITEM_SEARCH, "v1.0.0/item-search#filter"),
            (ConformanceClasses.FEATURES, "v1.0.0/ogcapi-features#fields"),
            (
                ConformanceClasses.COLLECTION_SEARCH,
                "v1.0.0-rc.1/collection-search#free-text",
            ),
        ],
    )
    def test_pattern_matches(
        self, conformance_class: ConformanceClasses, uri: str
    ) -> None:
        """Test pattern matches the class URI, with or without a fragment."""
        assert conformance_class.pattern.match(f"https://api.stacspec.org/{uri}")

    @pytest.mark.parametrize(
        "conformance_class, uri",
        [
            (
                ConformanceClasses.COLLECTIONS,
                "v1.0.0/collections/extensions/transaction",
            ),
            (
                ConformanceClasses.FEATURES,
                "v1.0.0/ogcapi-features/extensions/transaction",
            ),
            (
                ConformanceClasses.TRANSACTION,
                "v1.0.0/collections/extensions/transaction",
            ),
            (ConformanceClasses.COLLECTION_TRANSACTION, "v1.0.0/collections"),
            (ConformanceClasses.ITEM_SEARCH, "v1.0.0/item-searching"),
            (ConformanceClasses.FILTER, "v1.0.0/item-search"),
            (ConformanceClasses.CORE, "v1.1.0/core"),
        ],
    )
    def test_pattern_does_not_match(
        self, conformance_class: ConformanceClasses, uri: str
    ) -> None:
        """Test pattern rejects other classes, including path extensions."""
        assert not conformance_class.pattern.match(f"https://api.stacspec.org/{uri}")
