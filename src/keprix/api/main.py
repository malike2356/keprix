"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from keprix.config.constants import DOCS_URL, GITHUB_URL, PRODUCT_NAME, PRODUCT_VERSION
from keprix.config.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("Starting %s %s", PRODUCT_NAME, PRODUCT_VERSION)
    from keprix.database import engine, init_db
    await init_db(engine)
    yield
    logger.info("Shutting down %s", PRODUCT_NAME)
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=PRODUCT_NAME,
        version=PRODUCT_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        license_info={"name": "MIT", "url": GITHUB_URL},
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from keprix.api.v1.router import v1_router
    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
