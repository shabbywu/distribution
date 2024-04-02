import json
from pathlib import Path

import pytest

assets = Path(__file__).parent / "assets"


@pytest.fixture
def docker_manifest_schema1_dict():
    return json.loads((assets / "docker_manifest_schema1.json").read_text())


@pytest.fixture
def docker_manifest_schema2_dict():
    return json.loads((assets / "docker_manifest_schema2.json").read_text())


@pytest.fixture
def oci_manifest_schema1_dict():
    return json.loads((assets / "oci_manifest_schema1.json").read_text())


@pytest.fixture
def auth_response():
    return json.loads((assets / "auth_response.json").read_text())


@pytest.fixture
def image_json_dict():
    return json.loads((assets / "image_json.json").read_text())
