from pystac_client.conformance import ConformanceMixin


class TestConformanceMixin:
    def test_stac_core(self):
        conformance = ConformanceMixin()
        conformance.conformance = ['https://api.stacspec.org/v1.0.0-beta.2/core']
        assert conformance.conforms_to('core')

        # Legacy URIs
        conformance.conformance = ['https://api.stacspec.org/v1.0.0-beta.1/core']
        assert conformance.conforms_to('core')
