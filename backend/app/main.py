from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import v1_router
from app.core.config import get_settings
from app.core.errors import install_handlers
from app.core.redis import redis_pool
from app.modules.auth.router import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await redis_pool.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="business-template",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_env != "prod" else None,
        redoc_url="/api/redoc" if settings.app_env != "prod" else None,
        openapi_url="/api/openapi.json" if settings.app_env != "prod" else None,
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    install_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    @app.get("/healthz", tags=["infra"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
