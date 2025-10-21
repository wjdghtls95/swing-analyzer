from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api import include_all_routers
from app.config.settings import settings

# 앱 생성
app = FastAPI(debug=settings.DEBUG_MODE)

# 자동으로 app/api/* 모듈을 스캔해 라우터 전부 등록
include_all_routers(app)

app.openapi = lambda: get_openapi(
    title="AI Swing Analysis API",
    version="1.0.0",
    description="AI 골프 스윙 분석 API",
    routes=app.routes,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.FASTAPI_PORT, reload=True)
