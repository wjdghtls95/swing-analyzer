# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.10-slim AS builder

# 빌드 의존성 설치 (컴파일 도구 등)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 복사 (Docker 레이어 캐싱 최적화)
COPY requirements.txt .

# 가상환경에 설치 (프로덕션 이미지에서 복사하기 위해)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: Production
# ========================================
FROM python:3.10-slim

# 런타임 의존성만 설치 (빌드 도구 제외)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 빌더에서 가상환경 복사
COPY --from=builder /opt/venv /opt/venv

# 애플리케이션 코드 복사
COPY . .

# 필수 디렉토리 생성
RUN mkdir -p /app/data/logs /app/uploads /app/data/output

# 비-root 유저 생성 (보안)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 가상환경 활성화
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app:${PYTHONPATH}"

# 포트 노출
EXPOSE 8000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 실행
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
