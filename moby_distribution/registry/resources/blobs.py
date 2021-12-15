import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Optional, Tuple, Union
from urllib.parse import urlparse

from moby_distribution.registry import exceptions
from moby_distribution.registry.client import DockerRegistryV2Client, URLBuilder, default_client
from moby_distribution.registry.resources import RepositoryResource


class Blob(RepositoryResource):
    def __init__(
        self,
        repo: str,
        digest: Optional[str] = None,
        local_path: Optional[Union[Path, str]] = None,
        fileobj: Optional[BinaryIO] = None,
        client: DockerRegistryV2Client = default_client,
    ):
        super().__init__(repo, client)
        if isinstance(local_path, str):
            local_path = Path(local_path)

        self._accessor = Accessor(local_path=local_path, fileobj=fileobj)
        self.digest = digest

    def download(self, digest: Optional[str] = None):
        """download the blob from registry to `local_path` or `fileobj`"""
        digest = digest or self.digest
        if digest is None:
            raise RuntimeError("unknown digest")

        url = URLBuilder.build_blobs_url(self.client.api_base_url, repo=self.repo, digest=digest)
        resp = self.client.get(url=url, stream=True)
        with self._accessor.open(mode="wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024):
                fh.write(chunk)

    def upload(self) -> bool:
        """upload the blob from `local_path` or `fileobj` to the registry by streaming"""
        uuid, location = self._initiate_blob_upload()
        blob = BlobWriter(uuid, location, client=self.client)
        sha256 = hashlib.sha256()
        with self._accessor.open(mode="rb") as fh:
            chunk = fh.read(1024 * 1024 * 4)
            sha256.update(chunk)
            blob.write(chunk)

        digest = f"sha256:{sha256.hexdigest()}"
        if blob.commit(digest):
            self.digest = digest
            return True
        return False

    def upload_at_one_time(self):
        """upload the monolithic blob from `local_path` or `fileobj` to the registry at one time."""
        data = self._accessor.read_bytes()
        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"

        headers = {"content_type": "application/octect-stream"}
        params = {"digest": digest}

        uuid, location = self._initiate_blob_upload()
        resp = self.client.put(url=location, headers=headers, params=params, data=data)

        if not resp.ok:
            raise exceptions.RequestErrorWithResponse("failed to upload", status_code=resp.status_code, response=resp)
        self.digest = digest
        return True

    def _initiate_blob_upload(self) -> Tuple[str, str]:
        """Initiate a resumable blob upload.
        If successful, an uuid and upload location will be provided to complete the upload."""
        url = URLBuilder.build_upload_blobs_url(self.client.api_base_url, self.repo)
        resp = self.client.post(url=url)
        if resp.status_code != 202:
            raise exceptions.RequestError("Unexpected status code.", status_code=resp.status_code)

        uuid = resp.headers.get("docker-upload-uuid")
        location = resp.headers["location"]

        if uuid is None:
            uuid = location.split("/")[-1]

        if uuid == "":
            raise exceptions.RequestErrorWithResponse(
                "cannot retrieve docker upload UUID",
                status_code=resp.status_code,
                response=resp,
            )

        # Optionally, the location MAY be absolute (containing the protocol and/or hostname),
        # or it MAY be relative (containing just the URL path). For more information, see RFC 7231.
        if urlparse(location).netloc == "":
            location = f"{self.client.api_base_url}/{location.lstrip('/')}"
        return uuid, location


class BlobWriter:
    def __init__(self, uuid: str, location: str, client: DockerRegistryV2Client):
        self.uuid = uuid
        self.location = location
        self.client = client
        self._committed = False
        self._offset = 0

    def write(self, buffer: Union[bytes, bytearray]) -> int:
        headers = {
            "content-range": f"{self._offset}-{self._offset + len(buffer) - 1}",
            "content-type": "application/octet-stream",
        }
        resp = self.client.patch(url=self.location, data=buffer, headers=headers)

        if not resp.ok:
            raise exceptions.RequestErrorWithResponse(
                "fail to upload a chunk of blobs",
                status_code=resp.status_code,
                response=resp,
            )

        start_s, end_s = resp.headers["range"].split("-", 1)
        start, end = int(start_s), int(end_s)
        size = end - start + 1

        self.uuid = resp.headers["docker-upload-uuid"]
        self.location = resp.headers["location"]
        self._offset += size
        return size

    def commit(self, digest: str) -> bool:
        params = {"digest": digest}
        resp = self.client.put(url=self.location, params=params)
        if not resp.ok:
            raise exceptions.RequestErrorWithResponse(
                "can't commit an upload process",
                status_code=resp.status_code,
                response=resp,
            )
        self._committed = True
        return True


class Accessor:
    def __init__(self, local_path: Optional[Path] = None, fileobj: Optional[BinaryIO] = None):
        if not local_path and not fileobj:
            raise ValueError("Nothing to operate")
        if local_path and fileobj:
            raise ValueError("Cannot be provided `local_path` and `fileobj` at the same time")
        self.local_path = local_path
        self.fileobj = fileobj

    @contextmanager
    def open(self, *args, **kwargs):
        if self.fileobj:
            yield self.fileobj
        else:
            with self.local_path.open(*args, **kwargs) as fh:
                yield fh

    def read_bytes(self):
        if self.fileobj:
            self.fileobj.seek(0)
            return self.fileobj.read()
        return self.local_path.read_bytes()
