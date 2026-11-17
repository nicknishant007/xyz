"""FastAPI application entrypoint."""
from fastapi import FastAPI
from backend.api.routes import router
from backend.config.settings import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
