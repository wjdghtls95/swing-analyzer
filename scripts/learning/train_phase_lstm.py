"""
학습 스크립트 (데이터 로드 + 학습 루프 + 모델 저장)
phase_X.pt / phase_y.pt 로 간단 학습 → models/phase_model.pkl 저장
"""

import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from app.ml import PhaseLSTM

OUT_DIR = Path("artifacts/models")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    # 1) 데이터 로드
    df = pd.read_csv("artifacts/datasets/phase_dataset.csv")
    df = df.dropna()

    # features (elbow, knee, spine_tilt)
    X = df[["elbow", "knee", "spine_tilt"]].values.reshape(-1, 1, 3)  # (N, T=1, F=3)
    y = df["phase"].astype("category").cat.codes.values  # 문자열 phase → 숫자 인덱스

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    X_train = torch.tensor(X_train, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.long)
    X_val = torch.tensor(X_val, dtype=torch.float32)
    y_val = torch.tensor(y_val, dtype=torch.long)

    # 2) 모델/손실/옵티마이저"""
    # 학습 스크립트 (데이터 로드 + 학습 루프 + 모델 저장)
    # phase_X.pt / phase_y.pt 로 간단 학습 → models/phase_model.pkl 저장
    # """
    #
    # import torch
    # import torch.nn as nn
    # import torch.optim as optim
    # import pandas as pd
    # from pathlib import Path
    # from sklearn.model_selection import train_test_split
    # from app.ml import PhaseLSTM
    #
    # OUT_DIR = Path("artifacts/models")
    # OUT_DIR.mkdir(parents=True, exist_ok=True)
    #
    #
    # def main():
    #     # 1) 데이터 로드
    #     df = pd.read_csv("artifacts/datasets/phase_dataset.csv")
    #     df = df.dropna()
    #
    #     # features (elbow, knee, spine_tilt)
    #     X = df[["elbow", "knee", "spine_tilt"]].values.reshape(-1, 1, 3)  # (N, T=1, F=3)
    #     y = df["phase"].astype("category").cat.codes.values  # 문자열 phase → 숫자 인덱스
    #
    #     X_train, X_val, y_train, y_val = train_test_split(
    #         X, y, test_size=0.2, random_state=42
    #     )
    #
    #     X_train = torch.tensor(X_train, dtype=torch.float32)
    #     y_train = torch.tensor(y_train, dtype=torch.long)
    #     X_val = torch.tensor(X_val, dtype=torch.float32)
    #     y_val = torch.tensor(y_val, dtype=torch.long)
    #
    #     # 2) 모델/손실/옵티마이저
    #     model = PhaseLSTM(input_dim=3, hidden_dim=32, num_classes=len(set(y)))
    #     criterion = nn.CrossEntropyLoss()
    #     optimizer = optim.Adam(model.parameters(), lr=1e-3)
    #
    #     # 3) 학습 루프
    #     for epoch in range(10):
    #         model.train()
    #         optimizer.zero_grad()
    #         outputs = model(X_train)  # (N, T, C)
    #         outputs = outputs.squeeze(1)  # (N, C)
    #         loss = criterion(outputs, y_train)
    #         loss.backward()
    #         optimizer.step()
    #
    #         # Validation
    #         model.eval()
    #         with torch.no_grad():
    #             val_out = model(X_val).squeeze(1)
    #             val_loss = criterion(val_out, y_val)
    #             val_pred = val_out.argmax(dim=1)
    #             acc = (val_pred == y_val).float().mean().item()
    #
    #         print(
    #             f"[Epoch {epoch}] train_loss={loss.item():.4f} val_loss={val_loss.item():.4f} val_acc={acc:.3f}"
    #         )
    #
    #     # 4) 모델 저장
    #     ckpt = OUT_DIR / "phase_lstm.pt"
    #     torch.save(model.state_dict(), ckpt)
    #     print(f"[train_phase_lstm] model saved: {ckpt}")
    #
    #
    # if __name__ == "__main__":
    #     main()
    model = PhaseLSTM(input_dim=3, hidden_dim=32, num_classes=len(set(y)))
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    # 3) 학습 루프
    for epoch in range(10):
        model.train()
        optimizer.zero_grad()
        outputs = model(X_train)  # (N, T, C)
        outputs = outputs.squeeze(1)  # (N, C)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()

        # Validation
        model.eval()
        with torch.no_grad():
            val_out = model(X_val).squeeze(1)
            val_loss = criterion(val_out, y_val)
            val_pred = val_out.argmax(dim=1)
            acc = (val_pred == y_val).float().mean().item()

        print(
            f"[Epoch {epoch}] train_loss={loss.item():.4f} val_loss={val_loss.item():.4f} val_acc={acc:.3f}"
        )

    # 4) 모델 저장
    ckpt = OUT_DIR / "phase_lstm.pt"
    torch.save(model.state_dict(), ckpt)
    print(f"[train_phase_lstm] model saved: {ckpt}")


if __name__ == "__main__":
    main()
