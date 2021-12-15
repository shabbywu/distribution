# -*- coding: utf-8 -*-
import datetime
import pathlib
import random
import ssl
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from moby_distribution.spec.endpoint import APIEndpoint


def get_server_address():
    return "localhost", random.randint(10000, 40000)


@pytest.fixture
def certfile(tmp_path: pathlib.Path):
    """generate a self-signed certificate"""
    one_day = datetime.timedelta(1, 0, 0)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())

    public_key = private_key.public_key()
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(
        x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, 'localhost'),
            ]
        )
    )
    builder = builder.issuer_name(
        x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, 'localhost'),
            ]
        )
    )
    builder = builder.not_valid_before(datetime.datetime.today() - one_day)
    builder = builder.not_valid_after(datetime.datetime.today() + (one_day * 30))
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(public_key)
    builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
    builder = builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )
    certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256(), backend=default_backend())
    certificate_path = tmp_path / "certificate"
    certificate_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        + b"\n"
        + certificate.public_bytes(serialization.Encoding.PEM)
    )

    yield certificate_path
    certificate_path.unlink()


@pytest.fixture
def httpd():
    server_address = get_server_address()
    for i in range(10):
        try:
            with HTTPServer(server_address, SimpleHTTPRequestHandler) as httpd:
                yield httpd
                break
        except OSError:
            continue
    else:
        pytest.skip("failed to start http server")


@pytest.fixture
def http_server(httpd):
    sa = httpd.socket.getsockname()
    t = threading.Thread(target=httpd.serve_forever)
    t.start()
    yield sa[0], sa[1]
    httpd.shutdown()


@pytest.fixture
def https_server(httpd, certfile):
    httpd.socket = ssl.wrap_socket(httpd.socket, server_side=True, ssl_version=ssl.PROTOCOL_TLS, certfile=certfile)
    sa = httpd.socket.getsockname()
    t = threading.Thread(target=httpd.serve_forever)
    t.start()
    yield sa[0], sa[1]
    httpd.shutdown()


@pytest.fixture
def server(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize(
    "server, expected",
    [
        ("http_server", (False, False)),
        ("https_server", (True, False)),
    ],
    indirect=["server"],
)
def test_is_secure_repository(server, expected):
    assert APIEndpoint(url=f"{server[0]}:{server[1]}").is_secure_repository() == expected
