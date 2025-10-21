# keypoint_converter.py
import numpy as np
import json
from typing import Union


class KeypointConverter:
    def __init__(self, keypoints: Union[np.ndarray, list]):
        self._data = np.array(keypoints)

    def to_json_string(self, indent: int = 2) -> str:
        return json.dumps(self._data.tolist(), indent=indent)

    def to_numpy(self) -> np.ndarray:
        return self._data

    @classmethod
    def from_json_string(cls, json_str: str) -> "KeypointConverter":
        data = json.loads(json_str)
        return cls(data)
