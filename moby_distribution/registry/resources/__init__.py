from typing import Optional

from moby_distribution.registry.client import DefaultRegistryClient, RegistryHttpV2Client


class RepositoryResource:
    def __init__(
        self,
        repo: str,
        client: Optional[RegistryHttpV2Client] = DefaultRegistryClient,
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
    def client(self, v: RegistryHttpV2Client):
        self._client = v
