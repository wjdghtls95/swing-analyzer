from fastapi import APIRouter, HTTPException
from datetime import datetime
import psutil
import os
from app.config.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """
    기본 Health Check (Docker healthcheck용)
    
    Returns:
        dict: 기본 상태 정보
            - status: healthy/unhealthy
            - service: 서비스 이름
            - version: 버전 정보
            - timestamp: UTC 시간
    """
    try:
        # 메모리 사용량 체크 (90% 이상이면 unhealthy)
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            raise HTTPException(
                status_code=503,
                detail="Memory usage too high"
            )
        
        return {
            "status": "healthy",
            "service": "swing-analyzer",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health/detailed")
def health_check_detailed():
    """
    상세 Health Check (시스템 메트릭 포함)
    
    Returns:
        dict: 상세 상태 정보
            - status: healthy/unhealthy
            - service: 서비스 이름
            - version: 버전 정보
            - timestamp: UTC 시간
            - system: 시스템 리소스 (메모리, 디스크, CPU)
            - directories: 필수 디렉토리 존재 여부
            - environment: 환경 설정 정보
    """
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 디렉토리 존재 확인
        dirs_status = {
            "uploads": os.path.exists(settings.UPLOADS_DIR),
            "data": os.path.exists(settings.DATA_DIR),
            "logs": os.path.exists(settings.LOG_DIR),
            "config": os.path.exists(settings.CONFIG_DIR),
        }
        
        return {
            "status": "healthy",
            "service": "swing-analyzer",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": round(memory.percent, 2),
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": round(disk.percent, 2),
                },
                "cpu": {
                    "usage_percent": round(cpu_percent, 2),
                    "count": psutil.cpu_count(),
                }
            },
            "directories": dirs_status,
            "environment": {
                "debug_mode": settings.DEBUG_MODE,
                "llm_provider": settings.LLM_DEFAULT_PROVIDER,
                "env": settings.ENV,
                "fastapi_port": settings.FASTAPI_PORT,
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@router.get('/openai/health')
def llm_health(model: str = "gpt-4o-mini"):
    """
    LLM 연결 상태 체크
    
    Args:
        model (str): 테스트할 LLM 모델명
        
    Returns:
        dict: LLM 연결 상태
            - ok: True/False
            - provider: LLM provider 이름
            - model: 사용 중인 모델
            - echo: LLM 응답 (ping 테스트)
    """
    try:
        from app.llm.providers.openai_runtime import get_openai_adapter
        
        if settings.LLM_DEFAULT_PROVIDER == "noop":
            return {
                "ok": True,
                "provider": "noop",
                "message": "LLM disabled (noop mode)"
            }
        
        adapter = get_openai_adapter(settings.OPENAI_API_KEY)
        text = adapter.chat(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            temperature=0.0,
            max_tokens=8,
            timeout=30.0,
        )
        return {
            "ok": True,
            "provider": "openai",
            "model": model,
            "echo": text
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {e}"
        )


ROUTER = [router]
