import json
from pathlib import Path

try:
    from pydantic import __version__ as pydantic_version
except ImportError:
    # pydantic <= 1.8.2 does not have __version__
    from pydantic import VERSION as pydantic_version
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
    if pydantic_version.startswith("2."):
        return json.loads((assets / "auth_response.pydantic_v2.json").read_text())
    else:
        return json.loads((assets / "auth_response.pydantic_v1.json").read_text())


@pytest.fixture
def image_json_dict():
    if pydantic_version.startswith("2."):
        return json.loads((assets / "image_json.pydantic_v2.json").read_text())
    else:
        return json.loads((assets / "image_json.pydantic_v1.json").read_text())
