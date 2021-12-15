import random
import string
from io import BytesIO

import pytest

from moby_distribution.registry.resources.blobs import Blob
from moby_distribution.registry.resources.manifests import ManifestRef


class TestBlob:
    def test_download(
        self,
        repo,
        reference,
        registry_client,
    ):
        ref = ManifestRef(repo=repo, reference=reference, client=registry_client)
        manifest = ref.get()

        fh = BytesIO()
        Blob(fileobj=fh, repo=repo, digest=manifest.config.digest, client=registry_client).download()
        fh.seek(0)
        assert fh.read()

    @pytest.mark.parametrize("method", ["upload", "upload_at_one_time"])
    def test_upload(self, repo, reference, registry_client, method):
        fh1 = BytesIO("".join(random.choices(string.ascii_letters, k=1024)).encode())

        blob = Blob(fileobj=fh1, repo=repo, client=registry_client)
        assert getattr(blob, method)()

        fh2 = BytesIO()
        Blob(fileobj=fh2, repo=repo, client=registry_client, digest=blob.digest).download()

        fh1.seek(0)
        fh2.seek(0)

        assert fh1.read() == fh2.read()
