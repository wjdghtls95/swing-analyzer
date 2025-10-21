# Fallback defaults (settings에서 ENV 미지정 시 사용)
DEFAULT_VIDEO_FPS = 30
DEFAULT_VIDEO_HEIGHT = 720
DEFAULT_VIDEO_MIRROR = False

# thresholds 파일명 규칙(정보성)
THRESHOLDS_BASE_NAME = "thresholds.json"
THRESHOLDS_ENV_PATTERN = "thresholds.{ENV}.json"

# metrics → diagnosis key mapping (snake_case로 통일)
DIAG_KEY_MAP = {
    "elbow_avg": "elbow_diag",
    "knee_avg": "knee_diag",
}

# thresholds 키 alias (철자 혼용 방지)
ALIAS = {
    "elbow_avg": ["elbowAvg", "elbow"],
    "knee_avg": ["kneeAvg", "knee"],
}
