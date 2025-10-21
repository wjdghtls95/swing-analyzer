import torch
import numpy as np


class TorchPhaseAdapter:
    """
    PyTorch LSTM 체크포인트를 scikit-like 인터페이스로 감싸는 어댑터.
    - predict_proba(X): X (T, F) -> (T, C)
    - classes_: ["P2","P3","P4","P5","P6","P7","P8","P9"]
    """

    def __init__(self, model, device="cpu", classes=None, input_dim=3):
        self.model = model.to(device).eval()
        self.device = device
        self.classes_ = classes or [f"P{i}" for i in range(2, 10)]
        self.input_dim = input_dim  # 모델이 기대하는 F

    @torch.no_grad()
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        X: (T, F). LSTM은 배치/시간 차원이 필요하므로 (1, T, F)로 넣는다.
        출력: (T, C) 소프트맥스 확률
        """
        if X.ndim != 2:
            raise ValueError(f"X shape expected (T,F), got {X.shape}")
        T, F = X.shape
        if F != self.input_dim:
            # 필요 시 F를 줄이거나(열 선택) 늘리는 전처리를 여기서 수행
            raise ValueError(
                f"Feature dim mismatch: model expects {self.input_dim}, got {F}"
            )

        x = torch.tensor(X, dtype=torch.float32, device=self.device).unsqueeze(
            0
        )  # (1, T, F)
        logits = self.model(x)  # (1, T, C)
        logits = logits.squeeze(0)  # (T, C)
        prob = torch.softmax(logits, dim=-1).cpu().numpy()
        return prob
