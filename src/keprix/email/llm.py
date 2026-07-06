"""Lightweight LLM helper for email AI features."""

from __future__ import annotations

import json
import os
import re

from openai import AsyncOpenAI


async def llm_complete(prompt: str, *, system: str = "") -> str:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    base_url = os.environ.get("OPENROUTER_API_KEY") and "https://openrouter.ai/api/v1" or None
    model = os.environ.get("DEFAULT_LLM_MODEL", "gpt-4.1-mini")
    if model.startswith("openai/"):
        model = model.split("/", 1)[1]

    if not api_key:
        return _heuristic_response(prompt)

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=800,
    )
    return (response.choices[0].message.content or "").strip()


def _heuristic_response(prompt: str) -> str:
    if "priority" in prompt.lower():
        urgent_words = ("urgent", "asap", "immediately", "deadline", "overdue")
        if any(w in prompt.lower() for w in urgent_words):
            return json.dumps({"priority": "urgent", "tags": ["urgent"], "summary": "Urgent message requiring attention."})
        return json.dumps({"priority": "normal", "tags": ["general"], "summary": "Standard email message."})
    if "reply" in prompt.lower():
        return "Thank you for your message. I will follow up shortly."
    match = re.search(r"subject:\s*(.+)", prompt, re.I)
    subject = match.group(1).strip() if match else "this message"
    return f"This email about {subject} requests a response or provides an update."


async def summarize_email(subject: str, body: str, sender: str) -> dict[str, str | list[str]]:
    prompt = (
        f"Analyze this email and respond with JSON only.\n"
        f"Keys: summary (2 sentences), tags (up to 5 keywords), priority (urgent|normal|low).\n\n"
        f"From: {sender}\nSubject: {subject}\n\n{body[:4000]}"
    )
    raw = await llm_complete(prompt, system="You classify and summarize email. Output valid JSON only.")
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            return {
                "summary": str(data.get("summary", "")).strip(),
                "tags": [str(t) for t in data.get("tags", [])[:5]],
                "priority": str(data.get("priority", "normal")),
            }
    except json.JSONDecodeError:
        pass
    return {
        "summary": raw[:500] if raw else f"Email from {sender} about {subject}.",
        "tags": [],
        "priority": "normal",
    }


async def draft_reply(
    *,
    original_subject: str,
    original_body: str,
    original_sender: str,
    user_name: str = "User",
    signature: str = "",
) -> str:
    prompt = (
        f"Write a professional reply to this email. Match the tone of the original.\n"
        f"Sign as {user_name}.\n"
        f"Signature block (if any): {signature}\n\n"
        f"From: {original_sender}\nSubject: {original_subject}\n\n{original_body[:4000]}"
    )
    return await llm_complete(prompt, system="You draft concise, accurate email replies.")
