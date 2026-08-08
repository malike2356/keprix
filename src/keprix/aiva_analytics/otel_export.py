"""Optional OpenTelemetry-style metric export (K04).

Uses opentelemetry if installed; otherwise logs structured counters.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_counters: dict[str, Any] = {}
_meter = None
_tried = False


def _get_meter():
    global _meter, _tried
    if _tried:
        return _meter
    _tried = True
    try:
        from opentelemetry import metrics

        _meter = metrics.get_meter("keprix.aiva_analytics")
    except Exception:
        _meter = None
    return _meter


def export_metric_counter(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    attrs = {str(k): str(v) for k, v in (labels or {}).items()}
    meter = _get_meter()
    if meter is not None:
        counter = _counters.get(name)
        if counter is None:
            counter = meter.create_counter(name)
            _counters[name] = counter
        try:
            counter.add(float(value), attributes=attrs)
            return
        except Exception:
            logger.debug("otel counter add failed", exc_info=True)
    logger.debug("aiva_metric name=%s value=%s labels=%s", name, value, attrs)
