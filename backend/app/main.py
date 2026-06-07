from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Lifespan

from backend.app.api.router import api_router
from backend.app.core.settings import Settings, get_settings
from backend.app.services.answer_rewrite import warm_up_answer_rewrite
from backend.app.static_mount import mount_static_assets


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=_lifespan(settings),
    )
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(api_router, prefix="/api")
    mount_static_assets(app=app, settings=settings)
    return app


def _lifespan(settings: Settings) -> Lifespan[FastAPI]:
    @asynccontextmanager
    async def lifespan_context(app: FastAPI) -> AsyncGenerator[None]:
        _ = app
        if settings.llm_rewrite_warmup_enabled:
            _ = warm_up_answer_rewrite(settings=settings)
        yield

    return lifespan_context


app = create_app()
