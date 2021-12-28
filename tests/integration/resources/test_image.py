import gzip
import hashlib
import json
import tarfile

import pytest

from moby_distribution.registry.exceptions import ResourceNotFound
from moby_distribution.registry.resources.blobs import Blob
from moby_distribution.registry.resources.image import ImageRef, LayerRef
from moby_distribution.registry.resources.manifests import ManifestRef
from moby_distribution.registry.resources.tags import Tags


class TestImageRef:
    def test_save(self, tmp_path, repo, reference, registry_client):
        image_filepath = tmp_path / "image.tar"
        ImageRef.from_image(from_repo=repo, from_reference=reference, client=registry_client).save(image_filepath)

        with tarfile.open(image_filepath) as tarball:
            local_manifest = json.load(tarball.extractfile("manifest.json"))
            config = tarball.extractfile(local_manifest[0]["Config"]).read()

        digest = hashlib.sha256(config).hexdigest()
        manifest_filepath = tmp_path / "manifest"
        Blob(repo=repo, client=registry_client, local_path=manifest_filepath).download(digest=f"sha256:{digest}")

        assert manifest_filepath.read_bytes() == config

    def test_push_v2(self, repo, reference, temp_repo, temp_reference, registry_client):
        ref = ImageRef.from_image(
            from_repo=repo,
            from_reference=reference,
            to_repo=temp_repo,
            to_reference=temp_reference,
            client=registry_client,
        )

        with pytest.raises(ResourceNotFound):
            assert Tags(repo=temp_repo, client=registry_client).list() == []
        manifest = ref.push_v2()
        assert Tags(repo=temp_repo, client=registry_client).list() == [temp_reference]
        ManifestRef(repo=temp_repo, reference=temp_reference, client=registry_client).delete()
        assert Tags(repo=temp_repo, client=registry_client).list() == []

        for layer in manifest.layers:
            Blob(repo=temp_repo, digest=layer.digest, client=registry_client).delete()
        Blob(repo=temp_repo, digest=manifest.config.digest, client=registry_client).delete()

    def test_add_exists_layer(self, repo, reference, registry_client):
        ref = ImageRef.from_image(from_repo=repo, from_reference=reference, client=registry_client)
        ref.add_layer(ref.layers[0])
        image_json = ref.image_json
        assert ref.layers[0].digest == ref.layers[-1].digest
        assert image_json.rootfs.diff_ids[0] == image_json.rootfs.diff_ids[-1]

    def test_add_local_layer(self, tmp_path, repo, reference, registry_client):
        ref = ImageRef.from_image(from_repo=repo, from_reference=reference, client=registry_client)

        path = tmp_path / "layer.tar.gz"
        with tarfile.open(name=path, mode="w:gz"):
            pass

        content = path.read_bytes()
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        ref.add_layer(LayerRef(repo=repo, local_path=path, exists=False))
        image_json = ref.image_json
        assert ref.layers[-1].digest == digest
        assert "sha256:" + hashlib.sha256(gzip.decompress(content)).hexdigest() == image_json.rootfs.diff_ids[-1]

    def test_merge_layer_to_image(self, tmp_path, repo, reference, temp_reference, registry_client):
        ref = ImageRef.from_image(
            from_repo=repo,
            from_reference=reference,
            to_reference=temp_reference,
            client=registry_client,
        )

        path = tmp_path / "layer.tar.gz"
        with tarfile.open(name=path, mode="w:gz"):
            pass

        ref.add_layer(LayerRef(repo=repo, local_path=path, exists=False))
        manifest = ref.push_v2()

        assert sorted(Tags(repo=repo, client=registry_client).list()) == sorted([reference, temp_reference])
        Blob(repo=repo, digest=manifest.layers[-1].digest, client=registry_client).delete()
        Blob(repo=repo, digest=manifest.config.digest, client=registry_client).delete()
        ManifestRef(repo=repo, reference=temp_reference, client=registry_client).delete()
