import json

from moby_distribution.spec.image_json import ImageJSON


def test_image_json(image_json_dict):
    assert ImageJSON(**image_json_dict).json(exclude_unset=True) == json.dumps(image_json_dict)
