import pathlib
import hashlib
from typing import Generator, List, Optional, Union
from urllib.parse import urlparse

import libtrust
import requests

from moby_distribution.utils import get_private_key
from moby_distribution.spec import manifest
from moby_distribution import exceptions
from moby_distribution.auth import DockerRegistryTokenAuthentication
from moby_distribution.spec.auth import TokenResponse


class DistributionClient:
    """A Client implement APIs of Docker Registry HTTP API V2 and OCI Distribution Spec API

    spec: https://github.com/distribution/distribution/blob/main/docs/spec/api.md
    reference: https://github.com/distribution/distribution/tree/main/registry/client
    """

    def __init__(
        self,
        endpoint: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.session = requests.session()

        self.username = username
        self.password = password
        self._authed: Optional[TokenResponse] = None

    def v2(self) -> bool:
        """API Version Check."""
        url = f"{self.endpoint}/v2/"
        try:
            self._request(self.session.get, url=url)
        except exceptions.RequestError:
            return False
        return True

    def list_tags(self, repo: str) -> List[str]:
        """List all tags for the repo

        :param repo: Name of the target repository.
        :return:
        """
        url = f"{self.endpoint}/v2/{repo}/tags/list"
        data = self._request(self.session.get, url=url).json()
        return data["tags"]

    def pull_manifest_docker_v1(
        self, repo: str, reference: str = "latest"
    ) -> manifest.ManifestSchema1:
        """pull docker manifest schema v1"""
        headers = {
            "Content-Type": "application/vnd.docker.distribution.manifest.v1+prettyjws"
        }
        url = f"{self.endpoint}/v2/{repo}/manifests/{reference}"
        data = self._request(self.session.get, url=url, headers=headers).json()
        assert data["schemaVersion"] == 1
        return manifest.ManifestSchema1(**data)

    def pull_manifest_docker_v2(
        self, repo: str, reference: str = "latest"
    ) -> manifest.ManifestSchema2:
        """pull docker manifest schema v2"""
        headers = {
            "Accept": "application/vnd.docker.distribution.manifest.v2+json"
        }
        url = f"{self.endpoint}/v2/{repo}/manifests/{reference}"
        data = self._request(self.session.get, url=url, headers=headers).json()
        assert data["schemaVersion"] == 2
        return manifest.ManifestSchema2(**data)

    def pull_manifest_oci_v1(self, repo: str, reference: str = "latest"):
        """pull oci manifest schema v1"""
        headers = {
            "Accept": "application/vnd.oci.image.manifest.v1+json"
        }
        url = f"{self.endpoint}/v2/{repo}/manifests/{reference}"
        data = self._request(self.session.get, url=url, headers=headers).json()

        assert data["schemaVersion"] == 2, "This Registry does not support oci image"
        return manifest.OCIManifestSchema(**data)

    def pull_blob(
        self, repo: str, digest: str, stream: bool = False
    ) -> Union[bytes, Generator[bytes, None, None]]:
        """retrieve the blob from the registry identified by digest

        :param repo: Name of the target repository.
        :param digest: Digest of desired blob.
        :return:
        """
        url = f"{self.endpoint}/v2/{repo}/blobs/{digest}"
        resp = self._request(self.session.get, url=url, stream=stream)
        if stream:
            return resp.iter_content()
        return resp.content

    def push_manifest_v1(
        self, repo: str, item: manifest.ManifestSchema1, reference: str = "latest"
    ) -> bool:
        assert item.tag == reference

        url = f"{self.endpoint}/v2/{repo}/manifests/{item.tag}"
        private_key = get_private_key()

        data = item.json(
            include={
                "name",
                "tag",
                "architecture",
                "fsLayers",
                "history",
                "schemaVersion",
            }
        )
        js = libtrust.JSONSignature.new(data)
        js.sign(private_key)
        data = js.to_pretty_signature("signatures")

        headers = {"Content-Type": item.content_type, "Content-Length": len(data)}

        resp = self._request(self.session.put, url=url, data=data, headers=headers)
        return resp.ok

    def push_manifest_v2(
        self, repo: str, item: manifest.ManifestSchema2, reference: str = "latest"
    ) -> bool:
        url = f"{self.endpoint}/v2/{repo}/manifests/{reference}"
        data = item.json(include={"schemaVersion", "mediaType", "config", "layers"})

        headers = {"Content-Type": item.content_type, "Content-Length": len(data)}

        resp = self._request(self.session.put, url=url, data=data, headers=headers)
        return resp.ok

    def push_monolithic_blob(self, repo: str, filepath: str) -> bool:
        """push the blob to the registry"""
        url = self._start_blob_push(repo)
        with pathlib.Path(filepath).open(mode="rb") as fh:
            data = fh.read()
            digest = f"sha256:{hashlib.sha256(data).hexdigest()}"

        resp = self._request(
            self.session.put, url=url, data=data, params={"digest": digest}
        )
        return resp.ok

    def _start_blob_push(self, repo: str) -> str:
        """Start a blob upload process"""
        # TODO: 参考
        url = f"{self.endpoint}/v2/{repo}/blobs/uploads/"
        resp = self._request(self.session.post, url=url)
        if resp.status_code != 202:
            raise exceptions.RequestError(
                "Unexpected status code.", status_code=resp.status_code
            )

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
            location = f"{self.endpoint}/{location.lstrip('/')}"
        return location

    @property
    def authorization(self) -> str:
        if self._authed is None:
            return ""
        if self._authed.token:
            return f"Bearer {self._authed.token}"
        elif self._authed.access_token:
            return f"Bearer {self._authed.access_token}"
        raise RuntimeError("token not found.")

    def _request(self, method, *, should_retry: bool = True, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers["Authorization"] = self.authorization
        try:
            resp = self._validate_response(method(**kwargs), auto_auth=should_retry)
        except exceptions.RetryAgain:
            return self._request(method, should_retry=False, **kwargs)
        return resp

    def _validate_response(
        self, resp: requests.Response, auto_auth: bool = True
    ) -> requests.Response:
        if resp.status_code == 401:
            if auto_auth:
                www_authenticate = resp.headers["www-authenticate"]
                auth = DockerRegistryTokenAuthentication(www_authenticate)
                self._authed = auth.authenticate(
                    username=self.username, password=self.password
                )
                raise exceptions.RetryAgain
            raise exceptions.PermissionDeny

        if resp.status_code == 404:
            raise exceptions.ResourceNotFound

        if not resp.ok:
            raise exceptions.RequestError(message="未知异常", status_code=resp.status_code)
        return resp
