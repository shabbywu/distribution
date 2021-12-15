import json
from unittest import mock

import pytest
import requests
import requests_mock

from moby_distribution.registry.auth import DockerRegistryTokenAuthentication
from moby_distribution.registry.exceptions import AuthFailed


@pytest.fixture
def mock_adapter():
    session = requests.Session()
    adapter = requests_mock.Adapter()
    session.mount("mock://", adapter)
    with mock.patch("moby_distribution.registry.auth.requests", session):
        yield adapter


@pytest.fixture
def auth_response():
    return {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IlBZWU86VEVXVTpWN0pIOjI2SlY6QVFUWjpMSkMzOlNYVko6WEdIQTozNEYyOjJMQVE6WlJNSzpaN1E2In0.eyJpc3MiOiJhdXRoLmRvY2tlci5jb20iLCJzdWIiOiJqbGhhd24iLCJhdWQiOiJyZWdpc3RyeS5kb2NrZXIuY29tIiwiZXhwIjoxNDE1Mzg3MzE1LCJuYmYiOjE0MTUzODcwMTUsImlhdCI6MTQxNTM4NzAxNSwianRpIjoidFlKQ08xYzZjbnl5N2tBbjBjN3JLUGdiVjFIMWJGd3MiLCJhY2Nlc3MiOlt7InR5cGUiOiJyZXBvc2l0b3J5IiwibmFtZSI6InNhbWFsYmEvbXktYXBwIiwiYWN0aW9ucyI6WyJwdXNoIl19XX0.QhflHPfbd6eVF4lM9bwYpFZIV0PfikbyXuLx959ykRTBpe3CYnzs6YBK8FToVb5R47920PVLrh8zuLzdCr9t3w",
        "issued_at": "2009-11-10T23:00:00+00:00",
        "expires_in": 3600,
    }


class TestDockerRegistryTokenAuthentication:
    @pytest.mark.parametrize(
        "www_authenticate, expected",
        [
            (
                'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:samalba/my-app:pull,push"',
                {
                    "backend": "https://auth.docker.io/token",
                    "service": "registry.docker.io",
                    "scope": "repository:samalba/my-app:pull,push",
                },
            ),
            (
                'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:hello-world/hello-world:pull,push"',
                {
                    "backend": "https://auth.docker.io/token",
                    "service": "registry.docker.io",
                    "scope": "repository:hello-world/hello-world:pull,push",
                },
            ),
        ],
    )
    def test_properties(self, www_authenticate, expected):
        auth = DockerRegistryTokenAuthentication(www_authenticate)

        for k, v in expected.items():
            assert getattr(auth, k) == v

    def test_authenticate(self, mock_adapter, auth_response):
        www_authenticate = 'Bearer realm="mock://auth.docker.io/token",service="dummy",scope="dummy"'
        auth = DockerRegistryTokenAuthentication(www_authenticate)

        mock_adapter.register_uri("GET", "mock://auth.docker.io/token", json=auth_response)

        authed = auth.authenticate("username", "password")
        assert authed.json(exclude_unset=True) == json.dumps(auth_response)

    def test_authenticate_failed(self, mock_adapter):
        www_authenticate = 'Bearer realm="mock://auth.docker.io/token",service="dummy",scope="dummy"'
        auth = DockerRegistryTokenAuthentication(www_authenticate)

        mock_adapter.register_uri("GET", "mock://auth.docker.io/token", status_code=400)
        with pytest.raises(AuthFailed):
            auth.authenticate("username", "password")
