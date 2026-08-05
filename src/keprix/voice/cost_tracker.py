"""Phone call cost estimation."""

from __future__ import annotations


def estimate_call_cost(seconds: int, *, input_tokens: int = 0, output_tokens: int = 0) -> dict[str, float]:
    minutes = seconds / 60
    stt = minutes * 0.0059
    tts = minutes * 0.015
    twilio = minutes * 0.005
    agent = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)
    total = stt + tts + twilio + agent
    return {"stt_usd": round(stt, 4), "tts_usd": round(tts, 4), "twilio_usd": round(twilio, 4), "agent_usd": round(agent, 4), "total_usd": round(total, 4)}
