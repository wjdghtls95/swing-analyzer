"""
 LSTM 모델 정의
"""

import torch
import torch.nn as nn


class PhaseLSTM(nn.Module):
    """
    골프 스윙의 프레임 시퀀스 입력을 받아 각 프레임별 Phase(P2~P9 등)를 분류하는 LSTM 모델
    """

    def __init__(self, input_dim=9, hidden_dim=64, num_layers=1, num_classes=9):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        """
        x: (batch, time, features)
        return: (batch, time, num_classes)
        """
        out, _ = self.lstm(x)
        out = self.fc(out)
        return out
