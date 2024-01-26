from moby_distribution.registry.client import DockerRegistryV2Client, default_client
from moby_distribution.registry.utils import TypeTimeout, client_default_timeout


class RepositoryResource:
    def __init__(
        self,
        repo: str,
        client: DockerRegistryV2Client = default_client,
        *,
        timeout: TypeTimeout = client_default_timeout,
    ):
        self.repo = repo
        if client is not None:
            self._client = client
        self.timeout = timeout

    @property
    def client(self):
        if hasattr(self, "_client"):
            return self._client
        raise RuntimeError("Resource must bind Client")

    @client.setter
    def client(self, v: DockerRegistryV2Client):
        self._client = v
