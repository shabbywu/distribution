import os

import pytest

from moby_distribution.registry.client import DockerRegistryV2Client
from moby_distribution.spec.endpoint import APIEndpoint


@pytest.fixture
def registry_endpoint():
    return os.getenv("UNITTEST_REGISTRY_HOST")


@pytest.fixture(autouse=True)
def setup(registry_endpoint):
    if registry_endpoint is None:
        pytest.skip("integration not setup.")


@pytest.fixture
def registry_client(registry_endpoint):
    return DockerRegistryV2Client.from_api_endpoint(APIEndpoint(url=registry_endpoint))
