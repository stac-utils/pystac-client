# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Client.open` falls back to the `STAC_URL` environment variable if no url is provided as an argument [#48](https://github.com/stac-utils/pystac-client/pull/48)

### Fixed

- Running `stac-client` with no arguments no longer raises a confusing exception [#52](https://github.com/stac-utils/pystac-client/pull/52)

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

[Unreleased]: <https://github.com/stac-utils/pystac-client/compare/v0.1.1...main>
[v0.1.1]: <https://github.com/stac-utils/pystac-client/compare/v0.1.0..v0.1.1>
[v0.1.0]: <https://github.com/stac-utils/pystac-client/tree/v0.1.0>

