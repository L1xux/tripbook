"""FastAPI 앱 조립(엔트리포인트). / uvicorn이 호출. / 라우터·DB 초기화를 호출."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Tripbook API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    init_db()

    from app.routers import projects, photos, orders
    app.include_router(projects.router)
    app.include_router(photos.router)
    app.include_router(orders.router)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
