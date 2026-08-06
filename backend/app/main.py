"""FastAPI 앱을 조립한다.
uvicorn이 이 모듈의 app을 띄운다.
라우터를 등록하고 DB를 초기화한다."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Tripbook API", version="0.1.0")
    # 배포하면 프론트가 다른 도메인에서 오므로 그 주소만 허용한다.
    # 비어 있으면 로컬 개발로 보고 전부 허용한다.
    allowed = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware, allow_origins=allowed or ["*"], allow_methods=["*"], allow_headers=["*"]
    )
    # 라우터가 models를 import해 Base.metadata에 테이블을 등록한다 → 그 다음에 create_all
    from app.routers import projects, photos, orders
    init_db()
    app.include_router(projects.router)
    app.include_router(photos.router)
    app.include_router(orders.router)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
