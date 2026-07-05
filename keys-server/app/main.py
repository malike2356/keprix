from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.keys_admin import router as keys_admin_router
from app.api.webhooks import legacy_router as legacy_webhooks_router
from app.api.webhooks import router as webhooks_router
from app.db import close_pool, run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    yield
    await close_pool()


app = FastAPI(title="Petraclus Keys Server", version="0.1.0", lifespan=lifespan)
app.include_router(keys_admin_router)
app.include_router(webhooks_router)
app.include_router(legacy_webhooks_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "keys.petraclus.uk"}
