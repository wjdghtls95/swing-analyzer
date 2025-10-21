from fastapi import APIRouter, FastAPI
import importlib, pkgutil, inspect

# 이 패키지(root)
PACKAGE_NAME = __name__


def include_all_routers(app: FastAPI) -> None:
    """
    app/api 패키지의 모든 모듈을 스캔해서
    - ROUTERS: list[APIRouter]
    - 또는 top-level APIRouter 객체
    를 자동으로 app에 include.
    """
    # 현재 패키지 객체
    package = importlib.import_module(PACKAGE_NAME)

    # 패키지 하위의 모듈들 순회
    for modinfo in pkgutil.iter_modules(package.__path__):
        mod_name = modinfo.name
        # _ 로 시작하는 내부 모듈은 무시
        if mod_name.startswith("_"):
            continue

        module = importlib.import_module(f"{PACKAGE_NAME}.{mod_name}")

        # 1) ROUTERS 리스트가 있으면 그걸 우선 사용
        routers = getattr(module, "ROUTERS", None)
        if isinstance(routers, (list, tuple)):
            for r in routers:
                if _is_router(r):
                    app.include_router(r)
            continue

        # 2) 아니면 모듈 내 APIRouter 인스턴스들을 전부 include
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if _is_router(obj):
                app.include_router(obj)


def _is_router(obj) -> bool:
    try:
        return isinstance(obj, APIRouter)
    except Exception:
        # FastAPI가 아직 import 되기 전 edge case 방지
        return False
