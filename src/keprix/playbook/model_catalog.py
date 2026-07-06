"""Static catalog of known-good local models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CatalogModel:
    id: str
    name: str
    family: str
    size_b: float
    quant: str
    vram_gb: float
    ram_gb: float
    context_length: int
    benchmark_score: float
    vision_capable: bool
    release_year: int


CATALOG: list[CatalogModel] = [
    CatalogModel("llama3.3-70b-q4", "Llama 3.3 70B Q4", "llama", 70, "Q4_K_M", 42, 64, 128000, 88.0, False, 2024),
    CatalogModel("llama3.1-8b-q4", "Llama 3.1 8B Q4", "llama", 8, "Q4_K_M", 6, 12, 128000, 72.0, False, 2024),
    CatalogModel("llama3.1-70b-q4", "Llama 3.1 70B Q4", "llama", 70, "Q4_K_M", 42, 64, 128000, 85.0, False, 2024),
    CatalogModel("qwen2.5-7b-q4", "Qwen 2.5 7B Q4", "qwen", 7, "Q4_K_M", 5.5, 10, 32768, 74.0, False, 2024),
    CatalogModel("qwen2.5-14b-q4", "Qwen 2.5 14B Q4", "qwen", 14, "Q4_K_M", 10, 20, 32768, 78.0, False, 2024),
    CatalogModel("mistral-7b-q4", "Mistral 7B Q4", "mistral", 7, "Q4_K_M", 5.5, 10, 32768, 70.0, False, 2023),
    CatalogModel("phi-4", "Phi-4", "phi", 3.8, "Q4_K_M", 4, 8, 16384, 68.0, False, 2024),
    CatalogModel("gemma3-9b-q4", "Gemma 3 9B Q4", "gemma", 9, "Q4_K_M", 7, 14, 8192, 71.0, True, 2025),
    CatalogModel("deepseek-r1-7b-q4", "DeepSeek-R1 7B Q4", "deepseek", 7, "Q4_K_M", 5.5, 10, 32768, 76.0, False, 2025),
    CatalogModel("deepseek-v3-16b-q4", "DeepSeek-V3 16B Q4", "deepseek", 16, "Q4_K_M", 12, 24, 65536, 82.0, False, 2025),
    CatalogModel("falcon3-7b-q4", "Falcon 3 7B Q4", "falcon", 7, "Q4_K_M", 5.5, 10, 8192, 67.0, False, 2024),
    CatalogModel("smollm-1.7b-q4", "SmolLM 1.7B Q4", "smollm", 1.7, "Q4_K_M", 2, 4, 8192, 55.0, False, 2024),
    CatalogModel("codegemma-7b-q4", "CodeGemma 7B Q4", "gemma", 7, "Q4_K_M", 5.5, 10, 8192, 69.0, False, 2024),
]


def list_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": m.id,
            "name": m.name,
            "model_id": m.id,
            "family": m.family,
            "size_b": m.size_b,
            "quant": m.quant,
            "vram_gb": m.vram_gb,
            "ram_gb": m.ram_gb,
            "context_length": m.context_length,
            "benchmark_score": m.benchmark_score,
            "vision_capable": m.vision_capable,
            "release_year": m.release_year,
        }
        for m in CATALOG
    ]


def get_model(model_id: str) -> CatalogModel | None:
    for model in CATALOG:
        if model.id == model_id:
            return model
    return None
