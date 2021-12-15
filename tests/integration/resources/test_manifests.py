import hashlib

import pytest

from moby_distribution.registry.resources.manifests import ManifestRef, ManifestSchema1


@pytest.fixture
def expected_fixture(request):
    return request.getfixturevalue(request.param)


class TestManifestRef:
    @pytest.mark.parametrize(
        "media_type, expected_fixture",
        [
            (
                "application/vnd.docker.distribution.manifest.v1+prettyjws",
                "registry_manifest_schema1",
            ),
            (
                "application/vnd.docker.distribution.manifest.v2+json",
                "registry_manifest_schema2",
            ),
        ],
        indirect=["expected_fixture"],
    )
    def test_get(self, repo, reference, registry_client, media_type, expected_fixture):
        ref = ManifestRef(repo=repo, client=registry_client, reference=reference)
        assert ref.get(media_type).dict(exclude={"signatures"}, exclude_unset=True) == expected_fixture

    @pytest.mark.parametrize(
        "media_type, expected_fixture",
        [
            (
                "application/vnd.docker.distribution.manifest.v1+prettyjws",
                "registry_manifest_schema1_metadata",
            ),
            (
                "application/vnd.docker.distribution.manifest.v2+json",
                "registry_manifest_schema2_metadata",
            ),
        ],
        indirect=["expected_fixture"],
    )
    def test_get_metadata(self, repo, reference, registry_client, media_type, expected_fixture):
        ref = ManifestRef(repo=repo, client=registry_client, reference=reference)

        dumped = ref.get(media_type).json(indent=3, exclude_unset=True)
        descriptor = ref.get_metadata(media_type)

        assert descriptor.dict(exclude_unset=True) == expected_fixture
        assert descriptor.size == len(dumped)

        if media_type != ManifestSchema1.content_type():
            assert descriptor.digest == f"sha256:{hashlib.sha256(dumped.encode()).hexdigest()}"
