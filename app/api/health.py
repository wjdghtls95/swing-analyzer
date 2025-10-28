from fastapi import APIRouter, HTTPException
from app.config.settings import settings
from app.llm.providers.openai_runtime import get_openai_adapter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get('/openai/health')
def llm_health(model: str = "gpt-4o-mini"):
    try:
        adapter = get_openai_adapter(settings.OPENAI_API_KEY)
        text = adapter.chat(
            model=model,
            messages=[{"role":"user","content":"ping"}],
            temperature=0.0,
            max_tokens=8,
            timeout=30.0,
        )
        return {"ok": True, "model": model, "echo": text}

    except Exception as e:
        # 예외를 그대로 노출(임시)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


ROUTER = [router]
