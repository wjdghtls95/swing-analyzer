from app.analyze.extractor import PoseExtractor
from app.utils.keypoint_converter import KeypointConverter

video_path = "videos/tests.mp4"  # 테스트 영상

if __name__ == "__main__":
    extractor = PoseExtractor(step=5)
    npy_data, dict_data = extractor.extract_from_video(video_path)

    print("NumPy shape:", npy_data.shape)
    print("First landmark sample:", dict_data[0][0])

    converter = KeypointConverter(npy_data)
    json_str = converter.to_json_string()

    print("First JSON snippet:", json_str[:300])
