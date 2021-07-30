from pystac_client.conformance import ConformanceClasses


class TestConformanceMixin:
    def _test_stac_core(self):
        conformance.conformance = ['https://api.stacspec.org/v1.0.0-beta.2/core']
        assert conformance.conforms_to(ConformanceClasses.CORE)

        # Legacy URIs
        conformance.conformance = ['https://api.stacspec.org/v1.0.0-beta.1/core']
        assert conformance.conforms_to(ConformanceClasses.CORE)
