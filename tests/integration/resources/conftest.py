import json
import random
import string
from pathlib import Path

import pytest

assets = Path(__file__).parent / "assets"


@pytest.fixture
def repo() -> str:
    return "registry"


@pytest.fixture
def reference() -> str:
    return "2.7.1"


@pytest.fixture
def temp_repo() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=10))


@pytest.fixture
def temp_reference() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=10))


@pytest.fixture
def registry_manifest_schema1():
    return json.loads((assets / "registry_manifest_schema1.json").read_text())


@pytest.fixture
def registry_manifest_schema2():
    return json.loads((assets / "registry_manifest_schema2.json").read_text())


@pytest.fixture
def registry_manifest_schema1_metadata():
    return json.loads((assets / "registry_manifest_schema1_metadata.json").read_text())


@pytest.fixture
def registry_manifest_schema2_metadata():
    return json.loads((assets / "registry_manifest_schema2_metadata.json").read_text())


@pytest.fixture
def alpine_tar():
    return assets / "alpine.tar"


@pytest.fixture
def alpine_append_gzip_layer():
    return assets / "append.tar.gz"


@pytest.fixture
def alpine_append_layer():
    return assets / "append.tar"
