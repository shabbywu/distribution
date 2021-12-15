import json

from moby_distribution.registry.resources.blobs import Blob
from moby_distribution.registry.resources.manifests import ManifestRef
from moby_distribution.registry.resources.tags import Tags


def test_put_then_delete_v1(tmp_path, repo, reference, temp_reference, registry_client):
    manifest = ManifestRef(repo=repo, client=registry_client, reference=reference).get(
        "application/vnd.docker.distribution.manifest.v1+prettyjws"
    )

    manifest.tag = temp_reference
    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).put(manifest)

    assert set(Tags(repo=repo, client=registry_client).list()) == {
        reference,
        temp_reference,
    }

    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).delete()
    assert set(Tags(repo=repo, client=registry_client).list()) == {reference}


def test_put_then_delete_v2(tmp_path, repo, reference, temp_reference, registry_client):
    manifest = ManifestRef(repo=repo, client=registry_client, reference=reference).get(
        "application/vnd.docker.distribution.manifest.v2+json"
    )

    config_path = tmp_path / "config"
    blob = Blob(local_path=config_path, repo=repo, client=registry_client)

    # upload config
    blob.download(manifest.config.digest)
    config_path.write_text(json.dumps(json.loads(config_path.read_bytes()), indent=4))
    blob.upload()

    # upload manifest
    manifest.config.size = len(config_path.read_text())
    manifest.config.digest = blob.digest
    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).put(manifest)

    assert set(Tags(repo=repo, client=registry_client).list()) == {
        reference,
        temp_reference,
    }

    ManifestRef(repo=repo, client=registry_client, reference=temp_reference).delete()
    assert set(Tags(repo=repo, client=registry_client).list()) == {reference}
