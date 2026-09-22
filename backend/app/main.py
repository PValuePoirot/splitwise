"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.limiter import limiter
from app.routers import auth, expenses, groups, settlements


def create_app() -> FastAPI:
    app = FastAPI(
        title="Splitwise API",
        version="1.0.0",
        description="Group expense splitting with multi-payer, multi-debtor support.",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth.router)
    app.include_router(groups.router)
    app.include_router(expenses.router)
    app.include_router(settlements.router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
