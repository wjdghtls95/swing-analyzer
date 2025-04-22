import os
from dotenv import load_dotenv

env = os.getenv("ENV", "test")
dotenv_path = f".env.{env}"
load_dotenv(dotenv_path)

class Settings:
    PORT = int(os.getenv("FASTAPI_PORT", 8000))
    DEBUG = os.getenv("DEBUG_MODE", "false").lower() == "true"

settings = Settings()
