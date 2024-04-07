import json

from pydantic import __version__
from moby_distribution.spec.image_json import ImageJSON


def test_image_json(image_json_dict):
    if __version__.startswith("2."):
        assert (
            ImageJSON(**image_json_dict).model_dump(mode="json", exclude_unset=True)
            == image_json_dict
        )
    else:
        assert ImageJSON(**image_json_dict).json(exclude_unset=True) == json.dumps(
            image_json_dict
        )
