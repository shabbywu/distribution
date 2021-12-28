import json
from pathlib import Path

import pytest

asserts = Path(__file__).parent / "asserts"


@pytest.fixture
def docker_manifest_schema1_dict():
    return json.loads((asserts / "docker_manifest_schema1.json").read_text())


@pytest.fixture
def docker_manifest_schema2_dict():
    return json.loads((asserts / "docker_manifest_schema2.json").read_text())


@pytest.fixture
def oci_manifest_schema1_dict():
    return json.loads((asserts / "oci_manifest_schema1.json").read_text())


@pytest.fixture
def auth_response():
    return json.loads((asserts / "auth_response.json").read_text())


@pytest.fixture
def image_json_dict():
    return json.loads((asserts / "image_json.json").read_text())
