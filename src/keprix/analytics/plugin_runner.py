"""Analytics plugin runner."""

from __future__ import annotations

from collections import Counter
from statistics import mean, pstdev
from typing import Any, Callable


Plugin = Callable[..., Any]


class PluginRunner:
    def __init__(self) -> None:
        self.plugins: dict[str, Plugin] = {
            "sql_pull_data": self.sql_pull_data,
            "anomaly_detection": self.anomaly_detection,
            "paper_summary": self.paper_summary,
            "speech2text": self.speech2text,
            "text2speech": self.text2speech,
            "image2text": self.image2text,
            "text_classification": self.text_classification,
            "product_search": self.product_search,
        }

    def run(self, name: str, **kwargs: Any) -> Any:
        if name not in self.plugins:
            raise KeyError(f"Unknown analytics plugin: {name}")
        return self.plugins[name](**kwargs)

    def sql_pull_data(self, query: str = "", connection_name: str = "") -> dict:
        return {
            "status": "setup_required",
            "message": "Configure an approved SQL connection before pulling data.",
            "query": query,
            "connection_name": connection_name,
        }

    def anomaly_detection(self, values: list[float] | None = None, z_threshold: float = 2.0) -> dict:
        values = list(values or [])
        if not values:
            return {"anomalies": []}
        avg = mean(values)
        sd = pstdev(values) or 1.0
        anomalies = [
            {"index": index, "value": value, "z_score": (value - avg) / sd}
            for index, value in enumerate(values)
            if abs((value - avg) / sd) >= z_threshold
        ]
        return {"mean": avg, "stddev": sd, "anomalies": anomalies}

    def paper_summary(self, text: str = "") -> dict:
        sentences = [part.strip() for part in text.replace("\n", " ").split(".") if part.strip()]
        return {"summary": ". ".join(sentences[:3]), "sentence_count": len(sentences)}

    def speech2text(self, audio_path: str = "") -> dict:
        return {"status": "setup_required", "text": "", "audio_path": audio_path}

    def text2speech(self, text: str = "", voice: str = "default") -> dict:
        return {"status": "setup_required", "audio_url": "", "voice": voice, "text": text}

    def image2text(self, image_path: str = "") -> dict:
        return {"status": "setup_required", "text": "", "image_path": image_path}

    def text_classification(self, text: str = "", labels: list[str] | None = None) -> dict:
        labels = labels or ["general"]
        tokens = Counter(word.lower() for word in text.split())
        chosen = max(labels, key=lambda label: tokens.get(label.lower(), 0))
        return {"label": chosen, "scores": {label: tokens.get(label.lower(), 0) for label in labels}}

    def product_search(self, query: str = "") -> dict:
        return {"status": "setup_required", "query": query, "results": []}
