"""Hardware detection and model fit scoring."""

from __future__ import annotations

import platform
import shutil
from typing import Any

import psutil

from keprix.playbook.model_catalog import CatalogModel, list_catalog


def scan_hardware() -> dict[str, Any]:
    mem = psutil.virtual_memory()
    total_ram_gb = round(mem.total / (1024**3), 1)
    free_disk_gb = round(shutil.disk_usage("/").free / (1024**3), 1)
    cpu_cores = psutil.cpu_count(logical=True) or 1
    system_platform = platform.system().lower()
    arch = platform.machine()

    gpus: list[dict[str, Any]] = []
    gpu_vendor = "none"
    vram_total = 0.0
    nvidia = _detect_nvidia_gpus()
    if nvidia:
        gpus = nvidia
        gpu_vendor = "nvidia"
        vram_total = sum(g["vram_gb"] for g in gpus)
    elif system_platform == "darwin" and arch in {"arm64", "aarch64"}:
        gpu_vendor = "apple"
        unified = round(total_ram_gb * 0.75, 1)
        gpus = [{"index": 0, "name": "Apple Silicon", "vram_gb": unified}]
        vram_total = unified

    return {
        "platform": system_platform,
        "architecture": arch,
        "cpu_cores": cpu_cores,
        "total_ram_gb": total_ram_gb,
        "available_ram_gb": round(mem.available / (1024**3), 1),
        "free_disk_gb": free_disk_gb,
        "gpu_vendor": gpu_vendor,
        "gpus": gpus,
        "gpu_vram_gb": round(vram_total, 1),
        "has_gpu": bool(gpus),
    }


def _detect_nvidia_gpus() -> list[dict[str, Any]]:
    import subprocess

    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if proc.returncode != 0:
            return []
        gpus = []
        for idx, line in enumerate(proc.stdout.strip().splitlines()):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            vram_mb = float(parts[0])
            gpus.append({"index": idx, "name": parts[1], "vram_gb": round(vram_mb / 1024, 1)})
        return gpus
    except Exception:
        return []


def compute_fit_score(model: CatalogModel, hardware: dict[str, Any]) -> float:
    vram = hardware.get("gpu_vram_gb", 0) or 0
    ram = hardware.get("total_ram_gb", 0) or 0
    req_vram = model.vram_gb
    req_ram = model.ram_gb

    if hardware.get("has_gpu") and vram >= req_vram * 1.1:
        score = 1.0
    elif hardware.get("has_gpu") and vram >= req_vram * 0.85:
        score = 0.7
    elif ram >= req_ram * 1.2:
        score = 0.4
    else:
        score = 0.1

    if model.release_year >= 2024:
        score = min(1.0, score + 0.05)
    if model.benchmark_score >= 80:
        score = min(1.0, score + 0.03)
    return round(score, 2)


def rank_models(hardware: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    hw = hardware or scan_hardware()
    ranked = []
    for entry in list_catalog():
        model = CatalogModel(
            id=entry["id"],
            name=entry["name"],
            family=entry["family"],
            size_b=entry["size_b"],
            quant=entry["quant"],
            vram_gb=entry["vram_gb"],
            ram_gb=entry["ram_gb"],
            context_length=entry["context_length"],
            benchmark_score=entry["benchmark_score"],
            vision_capable=entry["vision_capable"],
            release_year=entry["release_year"],
        )
        fit = compute_fit_score(model, hw)
        ranked.append({**entry, "fit_score": fit})
    ranked.sort(key=lambda row: (row["fit_score"], row["benchmark_score"]), reverse=True)
    return ranked


def research_presets(hardware: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    hw = hardware or scan_hardware()
    vram = hw.get("gpu_vram_gb", 0) or 0
    if vram >= 24:
        large = "llama3.3-70b-q4"
        note_large = "24GB+ VRAM or dual GPU"
    else:
        large = "llama3.1-8b-q4"
        note_large = "Limited VRAM; using 8B preset"
    return {
        "small": {"model": "phi-4", "note": "4GB VRAM minimum"},
        "medium": {"model": "llama3.1-8b-q4", "note": "8GB VRAM"},
        "large": {"model": large, "note": note_large},
    }
