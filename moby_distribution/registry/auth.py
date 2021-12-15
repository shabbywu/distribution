# -*- coding: utf-8 -*-
import base64
import logging
from typing import Optional

import requests
from www_authenticate import parse

from moby_distribution.registry.exceptions import AuthFailed
from moby_distribution.spec.auth import TokenResponse

logger = logging.getLogger(__name__)


class DockerRegistryTokenAuthentication:
    """Docker Registry v2 authentication via central service

    spec: https://github.com/distribution/distribution/blob/main/docs/spec/auth/token.md
    """

    REQUIRE_KEYS = ["realm", "service"]

    def __init__(self, www_authenticate: str, offline_token: bool = True):
        self._www_authenticate = parse(www_authenticate)
        assert "bearer" in self._www_authenticate

        self.bearer = self._www_authenticate["bearer"]

        for key in self.REQUIRE_KEYS:
            assert key in self.bearer

        self.backend = self.bearer["realm"]
        self.service = self.bearer["service"]
        self.scope = self.bearer.get("scope", None)
        self.offline_token = offline_token

    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> TokenResponse:
        """Authenticate to the registry.
        If no username and password provided, will authenticate as the anonymous user.

        :param username: User name to authenticate as.
        :param password: User's password.
        :return:
        """
        params = {
            "service": self.service,
            "scope": self.scope,
            "client_id": username or "anonymous",
            "offline_token": self.offline_token,
        }
        headers = {}
        if username and password:
            auth = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"
        elif any([username, password]) and not all([username, password]):
            logger.warning("请同时提供 username 和 password!")

        resp = requests.get(self.backend, headers=headers, params=params)
        if resp.status_code != 200:
            raise AuthFailed(
                message="用户凭证校验失败, 请检查用户信息和操作权限",
                status_code=resp.status_code,
                response=resp,
            )
        return TokenResponse(**resp.json())
