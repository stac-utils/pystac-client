from pystac_client import ConformanceClasses


class TestConformanceClasses:
    def test_stac_core(self):
        assert ConformanceClasses.STAC_API_CORE.name == 'STAC API - Core'

        # Official conformance URI
        assert 'https://api.stacspec.org/v1.0.0-beta.1/core' == ConformanceClasses.STAC_API_CORE

        # Legacy URIs
        assert 'http://stacspec.org/spec/api/1.0.0-beta.1/core' != ConformanceClasses.STAC_API_CORE \
            and 'http://stacspec.org/spec/api/1.0.0-beta.1/core' in ConformanceClasses.STAC_API_CORE
