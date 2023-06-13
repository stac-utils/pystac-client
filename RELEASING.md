# Releasing

1. Determine the next version.
   We follow [semantic versioning](https://semver.org/).
2. Create a release branch named `release/vX.Y.Z`, where `X.Y.Z` is the next version.
3. Update [version.py](pystac_client/version.py) with the new version.
4. Update all cassettes: `pytest --record-mode rewrite`
5. Update [CHANGELOG.md](CHANGELOG.md).
   1. Add a new header under "Unreleased" with the new version and the date, e.g. `## [vX.Y.Z] - YYYY-MM-DD`.
   2. Audit the changelog section to ensure all changes are captured.
   3. Add a link reference for the new version after the Unreleased link reference at the bottom of the file.
      Follow the format from the previous version links.
6. If necessary, update the versions table in [the documentation](docs/index.rst)
7. (optional) Build the package locally and inspect its contents: `pip install build && python -m build`
8. Open a pull request for your `release/vX.Y.Z` branch against the appropriate branch (either `main` or a version branch, e.g. `v0.3`).
9. After pull request merge, create an annotated tag for your version, e.g. `git tag -a vX.Y.Z`.
10. Push the tag.
   This will trigger [the Github release workflow](.github/workflows/release.yml) and publish to PyPI.
11. [Create a new release on Github](https://github.com/stac-utils/pystac-client/releases/new) pointing to the new tag.
