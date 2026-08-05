"""Twilio provisioning plan helpers."""

from __future__ import annotations


def twilio_provisioning_plan(base_url: str, country: str = "GB") -> dict[str, str]:
    return {
        "provider": "twilio",
        "country": country,
        "voice_webhook": f"{base_url.rstrip('/')}/api/gateway/twilio/voice",
        "status_callback": f"{base_url.rstrip('/')}/api/gateway/twilio/status",
        "media_stream": f"{base_url.rstrip('/').replace('https://', 'wss://').replace('http://', 'ws://')}/api/gateway/twilio/stream/{{session_id}}",
        "estimated_monthly_number_cost": "GBP 1.15 plus usage",
    }
