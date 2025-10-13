import pandas as pd
from pathlib import Path
from app.ml.features import build_features

DATA = Path("artifacts/aggregated.csv")

def main():
    df = pd.read_csv(DATA)
    X = build_features(df)

    # 임시 타깃: 진단 문구를 OK/Not 으로 치환 (실제로는 별도 라벨 설계 필요)
    y = df.get("diag.AVG.elbow_diag").fillna("unknown")
    y = y.str.contains("적정 범위").astype(int)  # 1=OK, 0=Not

    print("[train] X shape:", X.shape, "y positive rate:", y.mean())
    # 여기에 모델 학습 코드 추가 (e.g., sklearn)

if __name__ == "__main__":
    main()