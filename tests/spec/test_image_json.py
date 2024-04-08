import json

try:
    from pydantic import __version__ as pydantic_version
except ImportError:
    # pydantic <= 1.8.2 does not have __version__
    from pydantic import VERSION as pydantic_version
from moby_distribution.spec.image_json import ImageJSON


def test_image_json(image_json_dict):
    if pydantic_version.startswith("2."):
        assert (
            ImageJSON(**image_json_dict).model_dump(mode="json", exclude_unset=True)
            == image_json_dict
        )
    else:
        assert ImageJSON(**image_json_dict).json(exclude_unset=True) == json.dumps(
            image_json_dict
        )
