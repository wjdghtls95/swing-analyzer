import pandas as pd

PHASE_KEYS = ["P4.elbow", "P4.knee", "P4.spine_tilt",
              "P7.elbow", "P7.knee", "P7.spine_tilt"]

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame(index=df.index)

    # 평균 메트릭
    for k in ["elbow_avg", "knee_avg"]:
        col = f"metrics.{k}"
        if col in df:
            feats[k] = df[col]

    # P4/P7 주요 수치
    for k in PHASE_KEYS:
        if k in df:
            feats[k.replace(".", "_")] = df[k]

    # 카테고리 인코딩(간단 라벨)
    if "club" in df:
        feats["club"] = df["club"].astype("category").cat.codes

    return feats