import hashlib
import json

import docker
import pytest
from moby_distribution.registry.resources.image import (
    ImageRef,
    LayerRef,
    ManifestSchema2,
)
from moby_distribution.registry.client import URLBuilder

try:
    from pydantic import __version__ as pydantic_version
except ImportError:
    # pydantic <= 1.8.2 does not have __version__
    from pydantic import VERSION as pydantic_version
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
        assert (
            ref.get(media_type).dict(exclude={"signatures"}, exclude_unset=True)
            == expected_fixture
        )

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
    def test_get_metadata(
        self, repo, reference, registry_client, media_type, expected_fixture
    ):
        ref = ManifestRef(repo=repo, client=registry_client, reference=reference)

        if pydantic_version.startswith("2."):
            dumped = json.dumps(
                ref.get(media_type).model_dump(mode="json", exclude_unset=True),
                indent=3,
            )
        else:
            dumped = ref.get(media_type).json(indent=3, exclude_unset=True)
        descriptor = ref.get_metadata(media_type)

        assert descriptor.dict(exclude_unset=True) == expected_fixture
        assert descriptor.size == len(dumped)

        if media_type != ManifestSchema1.content_type():
            assert (
                descriptor.digest
                == f"sha256:{hashlib.sha256(dumped.encode()).hexdigest()}"
            )


class TestIntegration:
    @pytest.fixture()
    def docker_cli(self):
        return docker.from_env()

    @pytest.fixture(autouse=True)
    def _init_image(
        self,
        registry_client,
        tmp_path,
        alpine_tar,
        alpine_append_layer,
        docker_cli,
        registry_netloc,
    ):
        ref = ImageRef.from_tarball(
            workplace=tmp_path,
            src=alpine_tar,
            to_repo="alpine",
            to_reference="manifest",
            client=registry_client,
        )
        ref.add_layer(LayerRef(local_path=alpine_append_layer))
        ref.push()

    def test_inspect(self, registry_client):
        url = URLBuilder.build_manifests_url(
            registry_client.api_base_url, repo="alpine", reference="manifest"
        )
        headers = {"Accept": ManifestSchema2.content_type()}
        data = registry_client.get(url=url, headers=headers).json()
        assert data["config"].get("urls", []) == []
        for layer in data["layers"]:
            assert layer.get("urls", []) == []
