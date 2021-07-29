# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.2.0-rc.1] - 2021-06-25

### Added

- `Client.open` falls back to the `STAC_URL` environment variable if no url is provided as an argument [#48](https://github.com/stac-utils/pystac-client/pull/48)
- New Search.get_pages() iterator function to retrieve pages as raw JSON, not as ItemCollections
- `StacApiIO` class added, subclass from PySTAC `StacIO`. A `StacApiIO` instance is used for all IO for a Client instance, and all requests
are in a single HTTP session.
- `conformance.CONFORMANCE_CLASSES` dictionary added containing all STAC API Capabilities from stac-api-spec
- `collections` subcommand to CLI, for saving all Collections in catalog as JSON

### Changed

- Update to use PySTAC 1.0.0-rc.2
- IO changed to use PySTAC's new StacIO base class. 
- `Search.item_collections()` renamed to `Search.get_item_collections()`
- `Search.item_collections()` renamed to `Search.get_items()`
- Conformance is checked by each individual function that requires a particular conformance
- STAC API testing URLs changed to updated APIs
- ItemSearch.get_pages function moved to StacApiIO class for general use

### Fixed

- Running `stac-client` with no arguments no longer raises a confusing exception [#52](https://github.com/stac-utils/pystac-client/pull/52)
- `Client.get_collections_list` [#44](https://github.com/stac-utils/pystac-client/issues/44)
- The regular expression used for datetime parsing [#59](https://github.com/stac-utils/pystac-client/pull/59)

### Removed

- `get_pages` and `simple_stac_resolver` functions from `pystac_client.stac_io` (The new StacApiIO class understands `Link` objects)
- `Client.search()` no longer accepts a `next_resolver` argument
- pystac.extensions modules, which were based on PySTAC's previous extension implementation, replaced in 1.0.0
- `stac_api_object.StacApiObjectMixin`, replaced with `conformance.ConformanceMixin`
- `conformance.ConformanceClass`, replaced with `conformance.ConformanceMixin`
- `conformance.ConformanceClasses`, replaced with `conformance.ConformanceMixin`
- PySTAC Collection objects can no longer be passed in as `collections` arguments to the `ItemSearch` class (just pass ids)

### Deprecated
- `Search.item_collections()`
- `Search.items()`

## [v0.1.1] - 2021-04-16

### Added

- `ItemSearch.items_as_collection` [#37](https://github.com/stac-utils/pystac-client/pull/37)
- Documentation [published on ReadTheDocs](https://pystac-client.readthedocs.io/en/latest/) [#46](https://github.com/stac-utils/pystac-client/pull/46)

### Fixed

- Include headers in STAC_IO [#38](https://github.com/stac-utils/pystac-client/pull/38)
- README updated to reflect actual CLI behavior

### Changed

- CLI: pass in heades as list of KEY=VALUE pairs

## [v0.1.0] - 2021-04-14

Initial release.

[Unreleased]: <https://github.com/stac-utils/pystac-client/compare/v0.2.0-rc.1...main>
[v0.2.0-rc.1]: <https://github.com/stac-utils/pystac-client/compare/v0.1.1..v0.2.0-rc.1>
[v0.1.1]: <https://github.com/stac-utils/pystac-client/compare/v0.1.0..v0.1.1>
[v0.1.0]: <https://github.com/stac-utils/pystac-client/tree/v0.1.0>

