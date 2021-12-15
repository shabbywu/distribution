from moby_distribution.registry.client import (
    DefaultRegistryClient,
    RegistryHttpV2Client,
    URLBuilder,
    set_default_client,
)
from moby_distribution.spec.endpoint import OFFICIAL_ENDPOINT


class TestRegistryHttpV2Client:
    def test_ping(self, registry_client):
        assert registry_client.ping()

    def test_set_default_client(self, registry_client, registry_endpoint):
        set_default_client(registry_client)
        assert DefaultRegistryClient.api_base_url == registry_endpoint

    def test_from_api_endpoint(self):
        set_default_client(RegistryHttpV2Client.from_api_endpoint(OFFICIAL_ENDPOINT))

        assert DefaultRegistryClient.api_base_url == "https://" + OFFICIAL_ENDPOINT.api_base_url


class TestURLBuilder:
    def test_build_v2_url(self):
        assert URLBuilder.build_v2_url("mock://a") == "mock://a/v2/"

    def test_build_blobs_url(self):
        assert URLBuilder.build_blobs_url("mock://a", "b", "c") == "mock://a/v2/b/blobs/c"

    def test_build_manifests_url(self):
        assert URLBuilder.build_manifests_url("mock://a", "b", "c") == "mock://a/v2/b/manifests/c"

    def test_build_upload_blobs_url(self):
        assert URLBuilder.build_upload_blobs_url("mock://a", "b") == "mock://a/v2/b/blobs/uploads/"

    def test_build_tags_url(self):
        assert URLBuilder.build_tags_url("mock://a", "b") == "mock://a/v2/b/tags/list"
