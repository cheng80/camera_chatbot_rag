from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from backend.app.api.router import api_router
from backend.app.core.settings import get_settings
from backend.app.static_mount import mount_static_assets


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        default_response_class=ORJSONResponse,
    )
    app.include_router(api_router, prefix="/api")
    mount_static_assets(app=app, settings=settings)
    return app


app = create_app()
