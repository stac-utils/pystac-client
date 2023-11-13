# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Recursion error in `get_items` [#608](https://github.com/stac-utils/pystac-client/pull/608)

### Removed

- Passing ``-q`` to the CLI rather than ``--query`` [#614](https://github.com/stac-utils/pystac-client/pull/614)

## [v0.7.5] - 2023-09-05

### Fixed

- `--matched` flag in CLI [#588](https://github.com/stac-utils/pystac-client/pull/588)

## [v0.7.4] - 2023-09-05

### Changed

- Don't provide a `limit` by default, trust the server to know its limits [#584](https://github.com/stac-utils/pystac-client/pull/584)

## [v0.7.3] - 2023-08-21

### Changed

- Raise more informative errors from CLI [#554](https://github.com/stac-utils/pystac-client/pull/554)
- Add `Retry` type hint to `StacApiIO` [#577](https://github.com/stac-utils/pystac-client/pull/577)

### Fixed

- Updated `get_items` signatures for PySTAC v1.8 [#559](https://github.com/stac-utils/pystac-client/pull/559), [#579](https://github.com/stac-utils/pystac-client/pull/579)

## [v0.7.2] - 2023-06-23

### Fixed

- Remove troublesome assertion [#549](https://github.com/stac-utils/pystac-client/pull/549)

## [v0.7.1] - 2023-06-13

### Fixed

- Remove unnecessary `typing_extensions` import [#541](https://github.com/stac-utils/pystac-client/pull/541)

## [v0.7.0] - 2023-06-12

### Added

- Timeout option added to `Client.open` [#463](https://github.com/stac-utils/pystac-client/pull/463), [#538](https://github.com/stac-utils/pystac-client/pull/538)
- Support for fetching catalog queryables [#477](https://github.com/stac-utils/pystac-client/pull/477)
- PySTAC Client specific warnings [#480](https://github.com/stac-utils/pystac-client/pull/480)
- Support for fetching and merging a selection of queryables [#511](https://github.com/stac-utils/pystac-client/pull/511)
- Better error messages for the CLI [#531](https://github.com/stac-utils/pystac-client/pull/531)
- `Modifiable` to our public API [#534](https://github.com/stac-utils/pystac-client/pull/534)
- `max_retries` parameter to `StacApiIO` [#532](https://github.com/stac-utils/pystac-client/pull/532)

### Changed

- Switched to Ruff from isort/flake8 [#457](https://github.com/stac-utils/pystac-client/pull/457)
- Move to `FutureWarning` from `DeprecationWarning` for item search interface functions that are to be removed [#464](https://github.com/stac-utils/pystac-client/pull/464)
- Consolidate contributing docs into one place [#478](https://github.com/stac-utils/pystac-client/issues/478)
- Use `pyproject.toml` instead of `setup.py` [#501](https://github.com/stac-utils/pystac-client/pull/501)
- Enable Ruff import sorting [#518](https://github.com/stac-utils/pystac-client/pull/518)

### Fixed

- `query` parameter in GET requests [#362](https://github.com/stac-utils/pystac-client/pull/362)
- Double encoding of `intersects` parameter in GET requests [#362](https://github.com/stac-utils/pystac-client/pull/362)
- Fix geometry instantiation in item-search-intersects.ipynb [#484](https://github.com/stac-utils/pystac-client/pull/484)
- Three tests that were false positives due to out-of-date cassettes [#491](https://github.com/stac-utils/pystac-client/pull/491)
- Max items checks when paging [#492](https://github.com/stac-utils/pystac-client/pull/492)
- `ItemSearch.url_with_parameters` no longer unquotes the url [#530](https://github.com/stac-utils/pystac-client/pull/530)

### Removed

- ``pystac_client.conformance.CONFORMANCE_URIS`` dictionary [#480](https://github.com/stac-utils/pystac-client/pull/480)

## [v0.6.1] - 2023-03-14

### Changed

- Bumped PySTAC dependency to >= 1.7.0 [#449](https://github.com/stac-utils/pystac-client/pull/449)

### Fixed

- Fix parse fail when header has multiple '=' characters [#440](https://github.com/stac-utils/pystac-client/pull/440)
- `Client.open` and `Client.from_file` now apply `headers`, etc to existing `stac_io` instances ([#439](https://github.com/stac-utils/pystac-client/pull/439))

## [v0.6.0] - 2023-01-27

### Added

- Python 3.11 support [#347](https://github.com/stac-utils/pystac-client/pull/347)
- `request_modifier` to `StacApiIO` to allow for additional authentication mechanisms (e.g. AWS SigV4) [#372](https://github.com/stac-utils/pystac-client/pull/372)
- *Authentication* tutorial, demonstrating how to use to the provided hooks to use both basic and AWS SigV4 authentication [#372](https://github.com/stac-utils/pystac-client/pull/372)
- CI checks for Windows and MacOS [#378](https://github.com/stac-utils/pystac-client/pull/378)
- Fallback to `STAC API - Item Search` when finding a single item in `CollectionClient` if `STAC API - Features` is not implemented [#379](https://github.com/stac-utils/pystac-client/pull/379)

### Fixed

- Stop iteration on an empty page [#338](https://github.com/stac-utils/pystac-client/pull/338)
- Some mishandled cases for datetime intervals [#363](https://github.com/stac-utils/pystac-client/pull/363)
- Collection requests when the Client's url ends in a '/' [#373](https://github.com/stac-utils/pystac-client/pull/373), [#405](https://github.com/stac-utils/pystac-client/pull/405)
- Parse datetimes more strictly [#364](https://github.com/stac-utils/pystac-client/pull/364)

### Removed

- Python 3.7 support [#347](https://github.com/stac-utils/pystac-client/pull/347)

## [v0.5.1] - 2022-09-19

### Added

- Added `ItemSearch.url_with_parameters` to get a formatted search url [#304](https://github.com/stac-utils/pystac-client/issues/304)

### Fixed

- Fix variable name in quickstart example [#316](https://github.com/stac-utils/pystac-client/pull/316)
- `StacApiIO.write_text_to_href` [#312](https://github.com/stac-utils/pystac-client/pull/312)
- Removed mention of STAC_URL in `Client.open` docstring [#317](https://github.com/stac-utils/pystac-client/pull/317)

## [v0.5.0] - 2022-08-19

### Added

- Added a new keyword `modifier` to various constructors like `Client.open()` [#259](https://github.com/stac-utils/pystac-client/issues/259)

### Fixed

- Fix type annotation of `Client._stac_io` and avoid implicit re-exports in `pystac_client.__init__.py` [#249](https://github.com/stac-utils/pystac-client/pull/249)
- Added `ItemSearch.pages`, `ItemSearch.pages_as_dicts`, `ItemSearch.item_collection`, and `ItemSearch.item_collection_as_dict`
  as replacements for various deprecated methods [#237](https://github.com/stac-utils/pystac-client/issues/237)
- Restored the previous behavior of ``Client.search()`` to return an unlimited number of items by default. [#273](https://github.com/stac-utils/pystac-client/pull/273)

### Deprecated

- `ItemSearch.item_collections` has been deprecated in favor of `ItemSearch.pages`. [#237](https://github.com/stac-utils/pystac-client/issues/237)

## [v0.4.0] - 2022-06-08

### Added

- Significantly improved type hints
- lru_cache to several methods [#167](https://github.com/stac-utils/pystac-client/pull/167)
- Direct item GET via ogcapi-features, if conformant [#166](https://github.com/stac-utils/pystac-client/pull/166)
- `py.typed` for downstream type checking [#163](https://github.com/stac-utils/pystac-client/pull/163)
- Added tutorial for using various geometry objects (e.g., shapely, geojson) as an Item Search intersects argument [#232](https://github.com/stac-utils/pystac-client/pull/232)

### Changed

- Item Search no longer defaults to returning an unlimited number of result Items from
  its "items" methods. The `max_items` parameter now defaults to 100 instead of None.
  Since the `limit` parameter also defaults to 100, in an ideal situation, only one request
  will be made to the server to retrieve all 100 items. Both of these parameters can be
  carefully adjusted upwards to align with the server's capabilities and the expected
  number of search results. [#208](https://github.com/stac-utils/pystac-client/pull/208)
- Better error message when trying to search a non-item-search-conforming catalog [#164](https://github.com/stac-utils/pystac-client/pull/164)
- Search `filter-lang` defaults to `cql2-json` instead of `cql-json` [#169](https://github.com/stac-utils/pystac-client/pull/169)
- Search `filter-lang` will be set to `cql2-json` if the `filter` is a dict, or `cql2-text` if it is a string [#169](https://github.com/stac-utils/pystac-client/pull/169)
- Search parameter `intersects` is now typed to only accept a str, dict, or object that implements `__geo_interface__` [#174](https://github.com/stac-utils/pystac-client/pull/174)
- Better error message when trying to open a Collection with `Client.open` [#222](https://github.com/stac-utils/pystac-client/pull/222)

### Deprecated

- Item Search methods `get_items()` and `get_item_collections()` have been renamed to
  `items()` and `item_collections()`. The original methods are now deprecated
  and may be removed as early as v0.5.0. [#206](https://github.com/stac-utils/pystac-client/pull/206)
- Item Search methods `get_all_items()` and `get_all_items_as_dict()` are now deprecated,
  and may be removed as early as v0.5.0.
  These have been deprecated because they have the potential to perform a large number
  of requests to the server and instantiate a large number of objects in memory.
  To a user, this is only visible as a large delay in the method call and/or the
  exhaustion of all available memory. The iterator methods `items()` or
  `item_collections()` should be used instead. [#206](https://github.com/stac-utils/pystac-client/pull/206)
- CLI parameter `-q` is now deprecated and may be removed as early as v0.5.0. Use `--query` instead. [#215](https://github.com/stac-utils/pystac-client/pull/215)

## Removed

- Client parameter `require_geojson_link` has been removed. [#165](https://github.com/stac-utils/pystac-client/pull/165)

### Fixed

- Search query parameter now has correct typing and handles Query Extension JSON format. [#220](https://github.com/stac-utils/pystac-client/pull/220)
- Search sortby parameter now has correct typing and handles both GET and POST JSON parameter formats. [#175](https://github.com/stac-utils/pystac-client/pull/175)
- Search fields parameter now has correct typing and handles both GET and POST JSON parameter formats. [#184](https://github.com/stac-utils/pystac-client/pull/184)
- Use pytest configuration to skip benchmarks by default (instead of a `skip` mark). [#168](https://github.com/stac-utils/pystac-client/pull/168)
- Methods retrieving collections incorrectly checked the existence of the OAFeat OpenAPI 3.0 conformance class
  (<http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30>) instead of the `STAC API - Collections`
  (<https://api.stacspec.org/v1.0.0-beta.1/collections>) or `STAC API - Features`
  (<https://api.stacspec.org/v1.0.0-beta.1/ogcapi-features>) conformance classes. [223](https://github.com/stac-utils/pystac-client/pull/223)

## [v0.3.5] - 2022-05-26

### Fixed

- Search against earth-search v0 failed with message "object of type 'Link' has no len()" [#179](https://github.com/stac-utils/pystac-client/pull/179)

## [v0.3.4] - 2022-05-18

### Changed

- Relaxed media type requirement for search links [#160](https://github.com/stac-utils/pystac-client/pull/160), [#165](https://github.com/stac-utils/pystac-client/pull/165)

## [v0.3.3] - 2022-04-28

### Added

- Add `--filter-lang` parameter to allow specifying other filter language to be used within the `--filter` parameter [#140](https://github.com/stac-utils/pystac-client/pull/140)
- CI checks against minimum versions of all dependencies and any pre-release versions of PySTAC [#144](https://github.com/stac-utils/pystac-client/pull/144)

### Changed

- Relaxed upper bound on PySTAC dependency [#144](https://github.com/stac-utils/pystac-client/pull/144)
- Bumped PySTAC dependency to >= 1.4.0 [#147](https://github.com/stac-utils/pystac-client/pull/147)

## [v0.3.2] - 2022-01-11

### Added

- `Client.search` accepts an optional `filter_lang` argument for `filter` requests [#128](https://github.com/stac-utils/pystac-client/pull/128)
- Added support for filtering the search endpoint using the `media_type` in `Client.open` [#142](https://github.com/stac-utils/pystac-client/pull/142)

### Fixed

- Values from `parameters` and `headers` arguments to `Client.open` and `Client.from_file` are now also used in requests made from `CollectionClient` instances
  fetched from the same API ([#126](https://github.com/stac-utils/pystac-client/pull/126))
- The tests folder is no longer installed as a package.

## [v0.3.1] - 2021-11-17

### Added

- Adds `--block-network` option to all test commands to ensure no network requests are made during unit tests
  [#119](https://github.com/stac-utils/pystac-client/pull/119)
- `parameters` argument to `StacApiIO`, `Client.open`, and `Client.from_file` to allow query string parameters to be passed to all requests
  [#118](https://github.com/stac-utils/pystac-client/pull/118)

### Changed

- Update min PySTAC version to 1.2
- Default page size limit set to 100 rather than relying on the server default
- Fetch single collection directly from endpoint in API rather than iterating through children [Issue #114](https://github.com/stac-utils/pystac-client/issues/114)

### Fixed

- `Client.get_collections` raised an exception when API did not publish `/collections` conformance class instead of falling back to using child links
  [#120](https://github.com/stac-utils/pystac-client/pull/120)

## [v0.3.0] - 2021-09-28

### Added

- Jupyter Notebook tutorials
- Basic CQL-JSON filtering [#100](https://github.com/stac-utils/pystac-client/pull/100)

### Changed

- Improved performance when constructing `pystac.ItemCollection` objects.
- Relax `requests` dependency [#87](https://github.com/stac-utils/pystac-client/pull/87)
- Use regular expressions for checking conformance classes [#97](https://github.com/stac-utils/pystac-client/pull/97)
- Reorganized documentation, updated all docs

### Fixed

- `ItemSearch` now correctly handles times without a timezone specifier [#92](https://github.com/stac-utils/pystac-client/issues/92)
- queries including `gsd` cast to string to float when using shortcut query syntax (i.e., "key=val" strings). [#98](https://github.com/stac-utils/pystac-client/pull/97)
- Documentation lints [#108](https://github.com/stac-utils/pystac-client/pull/108)

## [v0.2.0] - 2021-08-04

### Added

- `Client.open` falls back to the `STAC_URL` environment variable if no url is provided as an argument [#48](https://github.com/stac-utils/pystac-client/pull/48)
- New Search.get_pages() iterator function to retrieve pages as raw JSON, not as ItemCollections
- `StacApiIO` class added, subclass from PySTAC `StacIO`. A `StacApiIO` instance is used for all IO for a Client instance, and all requests
are in a single HTTP session, handle pagination and respects conformance
- `conformance.CONFORMANCE_CLASSES` dictionary added containing all STAC API Capabilities from stac-api-spec
- `collections` subcommand to CLI, for saving all Collections in catalog as JSON
- `Client.get_collections` overrides Catalog to use /collections endpoint if API conforms
- `Client.get_collection(<collection_id>)` for getting specific collection
- `Client.get_items` and `Client.get_all_items` override Catalog functions to use search endpoint instead of traversing catalog

### Changed

- Update to use PySTAC 1.1.0
- IO changed to use PySTAC's new StacIO base class.
- `Search.item_collections()` renamed to `Search.get_item_collections()`
- `Search.item()` renamed to `Search.get_items()`
- Conformance is checked by each individual function that requires a particular conformance
- STAC API testing URLs changed to updated APIs
- `ItemSearch.get_pages()` function moved to StacApiIO class for general use
- Logging is now enabled in the CLI in all cases.
  If data are being printed to stdout, logging goes to stderr.
  [#79](https://github.com/stac-utils/pystac-client/pull/79)
- Improved logging for GET requests (prints encoded URL)

### Removed

- `get_pages` and `simple_stac_resolver` functions from `pystac_client.stac_io` (The new StacApiIO class understands `Link` objects)
- `Client.search()` no longer accepts a `next_resolver` argument
- pystac.extensions modules, which were based on PySTAC's previous extension implementation, replaced in 1.0.0
- `stac_api_object.StacApiObjectMixin`, replaced with conformance checking in `StacApiIO`
- PySTAC Collection objects can no longer be passed in as `collections` arguments to the `ItemSearch` class (just pass ids)
- `Catalog.get_collection_list` (was alias to `get_child_links`) because made assumption about this being an API only. Also redundant with `Catalog.get_collections`
- `Search.item_collections()`
- `Search.items()`
- STAC_URL environment variable in Client.open(). url parameter in Client is now required
- STAC_URL environment variable in CLI. CLI now has a required positional argument for the URL

### Fixed

- Running `stac-client` with no arguments no longer raises a confusing exception [#52](https://github.com/stac-utils/pystac-client/pull/52)
- `Client.get_collections_list` [#44](https://github.com/stac-utils/pystac-client/issues/44)
- The regular expression used for datetime parsing [#59](https://github.com/stac-utils/pystac-client/pull/59)
- `Client.from_file` now works as expected, using `Client.open` is not required, although it will fetch STAC_URL from an envvar

## [v0.1.1] - 2021-04-16

### Added

- `ItemSearch.items_as_collection` [#37](https://github.com/stac-utils/pystac-client/pull/37)
- Documentation [published on ReadTheDocs](https://pystac-client.readthedocs.io/en/latest/) [#46](https://github.com/stac-utils/pystac-client/pull/46)

### Changed

- CLI: pass in heades as list of KEY=VALUE pairs

### Fixed

- Include headers in STAC_IO [#38](https://github.com/stac-utils/pystac-client/pull/38)
- README updated to reflect actual CLI behavior

## [v0.1.0] - 2021-04-14

Initial release.

[Unreleased]: <https://github.com/stac-utils/pystac-client/compare/v0.7.5...main>
[v0.7.5]: <https://github.com/stac-utils/pystac-client/compare/v0.7.4...v0.7.5>
[v0.7.4]: <https://github.com/stac-utils/pystac-client/compare/v0.7.3...v0.7.4>
[v0.7.3]: <https://github.com/stac-utils/pystac-client/compare/v0.7.2...v0.7.3>
[v0.7.2]: <https://github.com/stac-utils/pystac-client/compare/v0.7.1...v0.7.2>
[v0.7.1]: <https://github.com/stac-utils/pystac-client/compare/v0.7.0...v0.7.1>
[v0.7.0]: <https://github.com/stac-utils/pystac-client/compare/v0.6.1...v0.7.0>
[v0.6.1]: <https://github.com/stac-utils/pystac-client/compare/v0.6.0...v0.6.1>
[v0.6.0]: <https://github.com/stac-utils/pystac-client/compare/v0.5.1...v0.6.0>
[v0.5.1]: <https://github.com/stac-utils/pystac-client/compare/v0.5.0...v0.5.1>
[v0.5.0]: <https://github.com/stac-utils/pystac-client/compare/v0.4.0...v0.5.0>
[v0.4.0]: <https://github.com/stac-utils/pystac-client/compare/v0.3.5...v0.4.0>
[v0.3.5]: <https://github.com/stac-utils/pystac-client/compare/v0.3.4...v0.3.5>
[v0.3.4]: <https://github.com/stac-utils/pystac-client/compare/v0.3.3...v0.3.4>
[v0.3.3]: <https://github.com/stac-utils/pystac-client/compare/v0.3.2...v0.3.3>
[v0.3.2]: <https://github.com/stac-utils/pystac-client/compare/v0.3.1...v0.3.2>
[v0.3.1]: <https://github.com/stac-utils/pystac-client/compare/v0.3.0...v0.3.1>
[v0.3.0]: <https://github.com/stac-utils/pystac-client/compare/v0.2.0...v0.3.0>
[v0.2.0]: <https://github.com/stac-utils/pystac-client/compare/v0.1.1...v0.2.0>
[v0.1.1]: <https://github.com/stac-utils/pystac-client/compare/v0.1.0...v0.1.1>
[v0.1.0]: <https://github.com/stac-utils/pystac-client/tree/v0.1.0>
