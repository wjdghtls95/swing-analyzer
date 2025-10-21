from fastapi import APIRouter

router = APIRouter(prefix="default", tags=["Health"])


@router.get("/health")
def health_check():
    return {"status": "ok"}


ROUTER = [router]
