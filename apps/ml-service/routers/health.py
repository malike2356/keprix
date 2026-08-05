import httpx
from fastapi import APIRouter

from config import settings

router = APIRouter()


@router.get("")
async def health() -> dict:
    providers = {}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            await client.get(f"{settings.nllb_service_url.rstrip('/')}/health")
        providers["nllb"] = "ok"
    except Exception:
        providers["nllb"] = "unavailable"

    if settings.elevenlabs_api_key:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": settings.elevenlabs_api_key},
                )
            providers["elevenlabs"] = "ok" if response.status_code == 200 else "unavailable"
        except Exception:
            providers["elevenlabs"] = "unavailable"

    return {
        "status": "ok",
        "providers": providers,
        "models_loaded": [],
    }
