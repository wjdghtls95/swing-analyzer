def extract_basic_features(row: dict) -> dict:
    """
    로그 1개(row)에서 elbow/knee/spine_tilt 같은 핵심 피처만 뽑아낸다.
    필요하면 더 많은 피처(속도, 각도 변화량 등) 추가 가능.
    """
    return {
        "elbow": row.get("elbow"),
        "knee": row.get("knee"),
        "spine_tilt": row.get("spine_tilt"),
    }
