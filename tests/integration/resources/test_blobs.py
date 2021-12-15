import random
import string

import pytest

from moby_distribution.registry.resources.blobs import Blob
from moby_distribution.registry.resources.manifests import ManifestRef


class TestBlob:
    def test_download(
        self,
        tmp_path,
        repo,
        reference,
        registry_client,
    ):
        ref = ManifestRef(repo=repo, reference=reference, client=registry_client)
        manifest = ref.get()

        p = tmp_path / "config"
        Blob(local_path=p, repo=repo, client=registry_client, digest=manifest.config.digest).download()

        assert p.read_text()

    @pytest.mark.parametrize("method", ["upload", "upload_at_one_time"])
    def test_upload(self, tmp_path, repo, reference, registry_client, method):
        p = tmp_path / "p"
        p.write_text("".join(random.choices(string.ascii_letters, k=1024)))

        blob = Blob(local_path=p, repo=repo, client=registry_client)
        assert getattr(blob, method)()

        b = tmp_path / "b"
        Blob(local_path=b, repo=repo, client=registry_client, digest=blob.digest).download()

        assert b.read_text() == p.read_text()
