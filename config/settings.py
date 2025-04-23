import os
from dotenv import load_dotenv

# ENV 환경 변수를 기준으로 알맞은 .env 파일 로드
env = os.getenv("ENV", "test")
load_dotenv(dotenv_path=f".env.{env}")

class Settings:
    PORT: int = int(os.getenv("FASTAPI_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"

settings = Settings()