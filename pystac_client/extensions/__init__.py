from enum import Enum


class APIExtensions(str, Enum):
    """Identifiers for the `STAC API extensions
    <https://github.com/radiantearth/stac-api-spec/blob/master/extensions.md>`__ supported by this library."""

    CONTEXT = 'context'
    """Identifier for the `Context Extension
    <https://github.com/radiantearth/stac-api-spec/blob/master/item-search/README.md#context>`__."""
