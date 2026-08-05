"""FastAPI 앱을 조립한다.
uvicorn이 이 모듈의 app을 띄운다.
라우터를 등록하고 DB를 초기화한다."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Tripbook API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
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
