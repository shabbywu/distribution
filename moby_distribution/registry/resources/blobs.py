import hashlib
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Optional, Tuple, Union
from urllib.parse import urlparse

from moby_distribution.registry import exceptions
from moby_distribution.registry.client import DockerRegistryV2Client, URLBuilder, default_client
from moby_distribution.registry.resources import RepositoryResource
from moby_distribution.spec.base import Descriptor


class Blob(RepositoryResource):
    def __init__(
        self,
        repo: str,
        digest: Optional[str] = None,
        local_path: Optional[Union[Path, str]] = None,
        fileobj: Optional[Union[IO, 'HashSignWrapper']] = None,
        client: DockerRegistryV2Client = default_client,
    ):
        super().__init__(repo, client)
        if isinstance(local_path, str):
            local_path = Path(local_path)

        self.digest = digest
        self.local_path = local_path
        self.fileobj = fileobj
        self._accessor = None

    @property
    def accessor(self):
        if self._accessor is None:
            self._accessor = Accessor(local_path=self.local_path, fileobj=self.fileobj)
        return self._accessor

    def stat(self, digest: Optional[str] = None) -> Descriptor:
        """Obtain resource information without receiving all data."""
        digest = digest or self.digest
        if digest is None:
            raise RuntimeError("unknown digest")

        url = URLBuilder.build_blobs_url(self.client.api_base_url, repo=self.repo, digest=digest)
        resp = self.client.head(url=url)
        headers = resp.headers
        return Descriptor(
            # Content-Type: application/octet-stream
            mediaType=headers["Content-Type"],
            # The Content-Length in headers is the `Descriptor Message` size, but not the `Blob` itself.
            size=headers["Content-Length"],
            digest=headers.get("Docker-Content-Digest", digest),
            urls=[headers.get("Location", url)],
        )

    def download(self, digest: Optional[str] = None):
        """download the blob from registry to `local_path` or `fileobj`"""
        digest = digest or self.digest
        if digest is None:
            raise RuntimeError("unknown digest")

        url = URLBuilder.build_blobs_url(self.client.api_base_url, repo=self.repo, digest=digest)
        resp = self.client.get(url=url, stream=True)
        with self.accessor.open(mode="wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024):
                fh.write(chunk)

    def upload(self) -> Descriptor:
        """upload the blob from `local_path` or `fileobj` to the registry by streaming"""
        uuid, location = self._initiate_blob_upload()
        blob = BlobWriter(uuid, location, client=self.client)
        with self.accessor.open(mode="rb") as fh:
            signer = HashSignWrapper(fh=blob)
            shutil.copyfileobj(fsrc=fh, fdst=signer, length=1024 * 1024 * 64)

        digest = signer.digest()
        blob.commit(digest)
        self.digest = digest
        return self.stat()

    def upload_at_one_time(self) -> Descriptor:
        """upload the monolithic blob from `local_path` or `fileobj` to the registry at one time."""
        data = self.accessor.read_bytes()
        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"

        headers = {"content_type": "application/octect-stream"}
        params = {"digest": digest}

        uuid, location = self._initiate_blob_upload()
        resp = self.client.put(url=location, headers=headers, params=params, data=data)

        if resp.status_code != 201:
            raise exceptions.RequestErrorWithResponse("failed to upload", status_code=resp.status_code, response=resp)
        self.digest = digest
        return self.stat()

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

    def mount_from(self, from_repo: str) -> Descriptor:
        """Mount the blob from the given repo, if the client has read access to."""
        if self.digest is None:
            raise RuntimeError("unknown digest")

        url = URLBuilder.build_upload_blobs_url(self.client.api_base_url, self.repo)
        resp = self.client.post(url=url, params={"from": from_repo, "mount": self.digest})

        # If the blob is successfully mounted, the client will receive a `201` Created response
        if resp.status_code != 201:
            raise exceptions.RequestErrorWithResponse(
                f"failed to mount blob({self.digest}) from `{from_repo}`", status_code=resp.status_code, response=resp
            )
        return self.stat()

    def delete(self, digest: Optional[str] = None):
        """Delete the blob identified by repo and digest"""
        digest = digest or self.digest
        if digest is None:
            raise RuntimeError("unknown digest")

        url = URLBuilder.build_blobs_url(self.client.api_base_url, repo=self.repo, digest=digest)
        resp = self.client.delete(url=url)
        if resp.status_code != 202:
            raise exceptions.RequestErrorWithResponse(
                f"failed to delete blob({self.digest}) from `{self.repo}`", status_code=resp.status_code, response=resp
            )
        return True


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

        if resp.status_code != 202:
            raise exceptions.RequestErrorWithResponse(
                "fail to upload a chunk of blobs",
                status_code=resp.status_code,
                response=resp,
            )

        start_s, end_s = resp.headers["range"].split("-", 1)
        start, end = int(start_s), int(end_s)
        size = end - start + 1 - self._offset

        self.uuid = resp.headers["docker-upload-uuid"]
        self.location = resp.headers["location"]
        self._offset += size
        return size

    def commit(self, digest: str) -> bool:
        params = {"digest": digest}
        resp = self.client.put(url=self.location, params=params)
        if resp.status_code != 201:
            raise exceptions.RequestErrorWithResponse(
                "can't commit an upload process",
                status_code=resp.status_code,
                response=resp,
            )
        self._committed = True
        return True

    def tell(self) -> int:
        return self._offset


class Accessor:
    def __init__(self, local_path: Optional[Path] = None, fileobj: Optional[IO] = None):
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


class CounterIO:
    def __init__(self):
        self.size = 0

    def write(self, chunk: bytes):
        self.size += len(chunk)
        return len(chunk)

    def tell(self) -> int:
        return self.size


class HashSignWrapper:
    """A Wrapper can sign the content of fh when copying it.

    Usage:
    >>> import shutil
    >>> src = open("somewhere", mode="rb")
    >>> dest = HashSignWrapper(open("somewhere", mode="wb"))
    >>> shutil.copyfileobj(src, dest)
    """

    def __init__(self, fh: Optional[Union[IO, CounterIO, BlobWriter]] = None, constructor=hashlib.sha256):
        self._raw_fh = fh or CounterIO()
        self.signer = constructor()

    def write(self, chunk: bytes):
        self.signer.update(chunk)
        return self._raw_fh.write(chunk)

    def tell(self) -> int:
        return self._raw_fh.tell()

    def digest(self) -> str:
        """return hexdigest with hash method name"""
        return f"{self.signer.name}:{self.signer.hexdigest()}"
