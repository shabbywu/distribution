from moby_distribution.registry.client import DockerRegistryV2Client, default_client


class RepositoryResource:
    def __init__(
        self,
        repo: str,
        client: DockerRegistryV2Client = default_client,
    ):
        self.repo = repo
        if client is not None:
            self._client = client

    @property
    def client(self):
        if hasattr(self, "_client"):
            return self._client
        raise RuntimeError("Resource must bind Client")

    @client.setter
    def client(self, v: DockerRegistryV2Client):
        self._client = v
