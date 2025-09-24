from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.api.router import router as analyze_router
from app.config.settings import settings

app = FastAPI(debug=settings.DEBUG_MODE)

@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}

app.include_router(analyze_router, prefix="/analyze")

app.openapi = lambda: get_openapi(
    title="AI Swing Analysis API",
    version="1.0.0",
    description="AI 골프 스윙 분석 API",
    routes=app.routes,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.FASTAPI_PORT,
        reload=True
    )