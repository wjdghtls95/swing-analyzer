import asyncio
from contextlib import asynccontextmanager

# ffmpeg 동시 실행 상한 (필요시 .env/Settings로 빼기)
NORMALIZE_CONCURRENCY_LIMIT = 2
_normalize_semaphore = asyncio.Semaphore(NORMALIZE_CONCURRENCY_LIMIT)


@asynccontextmanager
async def normalize_slot():
    """
    표준화 작업의 동시 실행 개수를 제한 (혼잡 방지, 서버 안정성↑)
    """
    await _normalize_semaphore.acquire()
    try:
        yield
    finally:
        _normalize_semaphore.release()
