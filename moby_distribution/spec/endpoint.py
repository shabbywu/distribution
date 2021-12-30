import re
import socket
import ssl
from typing import Pattern, Tuple

from pydantic import BaseModel


class APIEndpoint(BaseModel):
    version: int = 2
    url: str
    official: bool = False

    def is_secure_repository(self) -> Tuple[bool, bool]:
        """Detect if the repository is secure

        :returns Tuple[bool, bool], the first one mean if the server support https?,
                                    the second one mean if the ssl certificate is valid?
        """
        match = url_regex().match(self.url)
        if not match:
            return False, False

        parts = match.groupdict()
        hostname = parts.get("domain") or parts.get("ipv4") or parts.get("ipv6")
        port = int(parts.get("port") or 443)

        try:
            context = ssl.create_default_context()
            s = context.wrap_socket(socket.socket(), server_hostname=hostname)
            s.connect((hostname, port))
            s.getpeercert()
        except ssl.SSLError as e:
            if e.reason == "CERTIFICATE_VERIFY_FAILED":
                return True, False
            elif e.reason == "WRONG_VERSION_NUMBER":
                return False, False
            return False, False
        return True, True

    @property
    def api_base_url(self) -> str:
        match = url_regex().match(self.url)
        if not match:
            raise ValueError("Invalid Url")

        parts = match.groupdict()
        hostname = parts["domain"] or parts["ipv4"] or parts["ipv6"]

        port = parts["port"]
        if not port:
            port = "443" if self.is_secure_repository()[0] else "80"

        path = parts["path"] or ""
        return f"{hostname}:{port}{path}"


_url_regex_cache = None


def url_regex() -> Pattern[str]:
    global _url_regex_cache
    if _url_regex_cache is None:
        _url_regex_cache = re.compile(
            r"(?:(?P<scheme>[a-z][a-z0-9+\-.]+)://)?"  # scheme https://tools.ietf.org/html/rfc3986#appendix-A
            r"(?:(?P<user>[^\s:/]*)(?::(?P<password>[^\s/]*))?@)?"  # user info
            r"(?:"
            r"(?P<ipv4>(?:\d{1,3}\.){3}\d{1,3})|"  # ipv4
            r"(?P<ipv6>\[[A-F0-9]*:[A-F0-9:]+\])|"  # ipv6
            r"(?P<domain>[^\s/:?#]+)"  # domain, validation occurs later
            r")?"
            r"(?::(?P<port>\d+))?"  # port
            r"(?P<path>/[^\s?#]*)?"  # path
            r"(?:\?(?P<query>[^\s#]+))?"  # query
            r"(?:#(?P<fragment>\S+))?",  # fragment
            re.IGNORECASE,
        )
    return _url_regex_cache


OFFICIAL_ENDPOINT = APIEndpoint(url="registry.hub.docker.com", official=True)
