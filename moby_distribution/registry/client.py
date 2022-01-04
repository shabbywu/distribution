from functools import partial
from typing import Optional, Type, cast

import requests

from moby_distribution.registry import exceptions
from moby_distribution.registry.auth import (
    AuthorizationProvider,
    BaseAuthentication,
    DockerRegistryTokenAuthentication,
)
from moby_distribution.registry.utils import LazyProxy
from moby_distribution.spec.endpoint import OFFICIAL_ENDPOINT, APIEndpoint


class DockerRegistryV2Client:
    """A Client implement APIs of Docker Registry HTTP API V2 and OCI Distribution Spec API

    spec: https://github.com/distribution/distribution/blob/main/docs/spec/api.md
    reference: https://github.com/distribution/distribution/tree/main/registry/client
    """

    @classmethod
    def from_api_endpoint(
        cls,
        api_endpoint: APIEndpoint = OFFICIAL_ENDPOINT,
        username: Optional[str] = None,
        password: Optional[str] = None,
        authenticator_class: Type[BaseAuthentication] = DockerRegistryTokenAuthentication,
    ):
        https_scheme = "https://"
        http_scheme = "http://"
        enable_https, certificate_valid = api_endpoint.is_secure_repository()
        if enable_https:
            client = cls(
                api_base_url=f"{https_scheme}{api_endpoint.api_base_url}",
                username=username,
                password=password,
                verify_certificate=certificate_valid,
                authenticator_class=authenticator_class,
            )
            if certificate_valid or client.ping():
                return client
        return cls(
            api_base_url=f"{http_scheme}{api_endpoint.api_base_url}",
            username=username,
            password=password,
            verify_certificate=False,
            authenticator_class=authenticator_class,
        )

    def __init__(
        self,
        api_base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_certificate: bool = True,
        authenticator_class: Type[BaseAuthentication] = DockerRegistryTokenAuthentication,
    ):
        if api_base_url.endswith("/"):
            api_base_url = api_base_url.rstrip("/")
        self.api_base_url = api_base_url
        self.session = requests.session()
        self.session.verify = verify_certificate

        self.username = username
        self.password = password
        self.authenticator_class = authenticator_class
        self._authed: Optional[AuthorizationProvider] = None

    def ping(self) -> bool:
        """API Version Check."""
        url = URLBuilder.build_v2_url(self.api_base_url)
        try:
            self._request(self.session.get, url=url)
        except exceptions.RequestError:
            return False
        return True

    @property
    def authorization(self) -> str:
        if self._authed is None:
            return ""
        return self._authed.provide()

    @property
    def get(self):
        return partial(self._request, self.session.get)

    @property
    def put(self):
        return partial(self._request, self.session.put)

    @property
    def patch(self):
        return partial(self._request, self.session.patch)

    @property
    def post(self):
        return partial(self._request, self.session.post)

    @property
    def delete(self):
        return partial(self._request, self.session.delete)

    @property
    def head(self):
        return partial(self._request, self.session.head)

    def _request(self, method, *, should_retry: bool = True, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers["Authorization"] = self.authorization
        try:
            resp = self._validate_response(method(**kwargs), auto_auth=should_retry)
        except exceptions.RetryAgain:
            return self._request(method, should_retry=False, **kwargs)
        return resp

    def _validate_response(self, resp: requests.Response, auto_auth: bool = True) -> requests.Response:
        if resp.status_code == 401:
            if auto_auth:
                www_authenticate = resp.headers["www-authenticate"]
                auth = self.authenticator_class(www_authenticate)
                self._authed = auth.authenticate(username=self.username, password=self.password)
                raise exceptions.RetryAgain
            raise exceptions.PermissionDeny

        if resp.status_code == 404:
            raise exceptions.ResourceNotFound

        if not resp.ok:
            raise exceptions.RequestErrorWithResponse(message=resp.text, status_code=resp.status_code, response=resp)
        return resp


class URLBuilder:
    @staticmethod
    def build_v2_url(endpoint: str) -> str:
        return f"{endpoint}/v2/"

    @staticmethod
    def build_blobs_url(endpoint: str, repo: str, digest: str) -> str:
        return f"{endpoint}/v2/{repo}/blobs/{digest}"

    @staticmethod
    def build_manifests_url(endpoint: str, repo: str, reference: str) -> str:
        return f"{endpoint}/v2/{repo}/manifests/{reference}"

    @staticmethod
    def build_upload_blobs_url(endpoint: str, repo: str) -> str:
        return f"{endpoint}/v2/{repo}/blobs/uploads/"

    @staticmethod
    def build_tags_url(endpoint: str, repo: str) -> str:
        return f"{endpoint}/v2/{repo}/tags/list"


default_client = cast(
    DockerRegistryV2Client, LazyProxy(lambda: DockerRegistryV2Client.from_api_endpoint(OFFICIAL_ENDPOINT))
)


def set_default_client(client: DockerRegistryV2Client):
    default_client.__dict__["_wrapped"] = client
