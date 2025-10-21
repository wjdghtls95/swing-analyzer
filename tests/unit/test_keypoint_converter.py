import numpy as np

from app.utils.keypoint_converter import KeypointConverter


def test_keypoint_json_roundtrip():
    dummy = np.random.rand(10, 33, 4)
    converter = KeypointConverter(dummy)
    json_str = converter.to_json_string()

    restored = KeypointConverter.from_json_string(json_str).to_numpy()
    assert restored.shape == (10, 33, 4)
    assert np.allclose(dummy, restored)
