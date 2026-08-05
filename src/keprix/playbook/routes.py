"""Local model playbook HTTP routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.playbook.benchmark import run_model_benchmark
from keprix.playbook.hwfit import rank_models, research_presets, scan_hardware
from keprix.playbook.jobs import get_playbook_job_store, run_download_job
from keprix.playbook.model_catalog import get_model

router = APIRouter(prefix="/api/playbook", tags=["playbook"])


def _user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if isinstance(user, dict):
        uid = str(user.get("id") or user.get("username") or "").strip()
        if uid:
            return uid
    header = request.headers.get("x-user-id", "").strip()
    if header:
        return header
    return "local"


class BenchmarkBody(BaseModel):
    model_id: str = Field(..., min_length=1)
    backend: str = "ollama"


@router.get("/scan")
async def hardware_scan() -> dict[str, Any]:
    return scan_hardware()


@router.get("/models")
async def list_models() -> dict[str, Any]:
    hardware = scan_hardware()
    models = rank_models(hardware)
    return {"hardware": hardware, "models": models, "count": len(models)}


@router.get("/models/{model_id}")
async def model_detail(model_id: str) -> dict[str, Any]:
    model = get_model(model_id)
    if model is None:
        raise HTTPException(404, "Model not found")
    hardware = scan_hardware()
    from keprix.playbook.hwfit import compute_fit_score

    fit = compute_fit_score(model, hardware)
    return {
        "id": model.id,
        "name": model.name,
        "family": model.family,
        "size_b": model.size_b,
        "quant": model.quant,
        "vram_gb": model.vram_gb,
        "context_length": model.context_length,
        "benchmark_score": model.benchmark_score,
        "vision_capable": model.vision_capable,
        "fit_score": fit,
    }


@router.post("/models/{model_id}/download")
async def start_download(model_id: str, request: Request) -> dict[str, str]:
    if get_model(model_id) is None:
        raise HTTPException(404, "Model not found")
    store = get_playbook_job_store()
    job = store.create(user_id=_user_id(request), job_type="download", model_id=model_id)
    import asyncio

    asyncio.create_task(run_download_job(job))
    return {"job_id": job.id, "status": job.status}


@router.get("/models/{model_id}/download/status")
async def download_status(model_id: str, request: Request) -> StreamingResponse:
    store = get_playbook_job_store()
    user = _user_id(request)
    jobs = [j for j in store._jobs.values() if j.model_id == model_id and j.user_id == user]
    if not jobs:
        raise HTTPException(404, "No download job found")

    job = sorted(jobs, key=lambda j: j.started_at, reverse=True)[0]

    async def generate():
        last_len = 0
        while job.status == "running":
            if len(job.logs) > last_len:
                payload = {"progress_pct": job.progress_pct, "log": job.logs[last_len:]}
                last_len = len(job.logs)
                yield f"data: {json.dumps(payload)}\n\n"
            import asyncio

            await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'status': job.status, 'progress_pct': job.progress_pct})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/models/{model_id}/serve")
async def start_serve(model_id: str, request: Request) -> dict[str, Any]:
    if get_model(model_id) is None:
        raise HTTPException(404, "Model not found")
    store = get_playbook_job_store()
    port = 11434
    store.register_serving(model_id, "ollama", port)
    job = store.create(user_id=_user_id(request), job_type="serve", model_id=model_id)
    job.status = "complete"
    job.completed_at = job.started_at
    job.result = {"port": port, "backend": "ollama"}
    store.append_log(job, f"Registered {model_id} on ollama port {port}")
    return {"job_id": job.id, "port": port, "backend": "ollama"}


@router.post("/models/{model_id}/stop")
async def stop_serve(model_id: str) -> dict[str, bool]:
    store = get_playbook_job_store()
    stopped = store.stop_serving(model_id)
    return {"stopped": stopped}


@router.get("/serving")
async def list_serving() -> dict[str, Any]:
    store = get_playbook_job_store()
    return {"serving": store.list_serving()}


@router.get("/serving/health")
async def serving_health(port: int = 11434) -> dict[str, Any]:
    """Ping a local Ollama (or OpenAI-compatible) base from the API host."""
    import httpx

    base = f"http://127.0.0.1:{port}"
    candidates = [f"{base}/api/tags", f"{base}/v1/models"]
    last_error = "unreachable"
    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in candidates:
            try:
                response = await client.get(url)
                if response.status_code < 500:
                    return {
                        "ok": True,
                        "port": port,
                        "base_url": f"{base}/v1",
                        "probe_url": url,
                        "status_code": response.status_code,
                    }
                last_error = f"HTTP {response.status_code}"
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
    return {
        "ok": False,
        "port": port,
        "base_url": f"{base}/v1",
        "error": last_error,
        "fix": "Start the Ollama daemon (`ollama serve`) or fix the serve port.",
    }


@router.post("/benchmark")
async def benchmark(body: BenchmarkBody) -> dict[str, Any]:
    if get_model(body.model_id) is None:
        raise HTTPException(404, "Model not found")
    store = get_playbook_job_store()
    serving = store._serving.get(body.model_id)
    port = int(serving.get("port", 11434)) if serving else 11434
    try:
        return await run_model_benchmark(body.model_id, body.backend, port=port)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/research-presets")
async def get_research_presets() -> dict[str, dict[str, str]]:
    return research_presets()


@router.get("/jobs/{job_id}/logs")
async def job_logs(job_id: str, request: Request) -> dict[str, Any]:
    store = get_playbook_job_store()
    job = store.get(job_id, _user_id(request))
    if job is None:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "logs": job.logs,
        "result": job.result,
    }
