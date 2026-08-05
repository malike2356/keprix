# keprix - Prompt 46: Voice Wake Words with Gateway Ownership

## Context

Reference: `planning/agents-to-adopt/openclaw/docs/nodes/voicewake.md`.

Prompt 27 specifies voice input and output: speech-to-text, text-to-speech, language detection, and channel-specific voice delivery. What it does not define is the always-on listening posture that precedes all of that: wake word detection.

Wake word detection is the layer that turns a device (desktop app, mobile, smart speaker) from a passive playback device into an agent that can be activated by saying "Hey keprix" or any configured trigger phrase. Without this, the user must manually activate a microphone for every interaction. With it, the agent can be ambient: present but silent, waiting for its name.

The design constraint from OpenClaw that shapes everything here: wake words are a global list owned by the gateway, not per-device. Every node (desktop, mobile, CLI, web) can edit the trigger list, but they all share one list. A user who changes their wake word on their phone immediately changes it on their laptop. This prevents the frustrating state where a user updates their trigger on one device and nothing works on another.

This prompt builds the wake word registry (gateway-owned, broadcast on change), the per-node enable/disable toggle, and the integration with the voice input pipeline.

---

## File Structure

```
keprix/backend/voice/
    wake.py             - WakeWordRegistry: storage, broadcast, protocol
    detector.py         - WakeWordDetector: local keyword detection (optional/pluggable)
    routes.py           - API endpoints

keprix/ui/web/src/app/(workspace)/settings/voice/
    wake-words/page.tsx - wake word management UI

keprix/ui/desktop/src/voice/
    wake_detector.ts    - desktop app wake word listener (wraps native STT or pocketsphinx)
```

---

## Wake Word Registry

```python
# keprix/backend/voice/wake.py

import json
from pathlib import Path

WAKE_WORD_DEFAULTS = ["keprix", "hey keprix"]
WAKE_WORD_MAX_COUNT = 10
WAKE_WORD_MAX_LENGTH = 40   # characters per trigger phrase


class WakeWordRegistry:
    """
    Gateway-owned registry for wake word triggers.
    All nodes share this list. Changes are broadcast to connected nodes.
    """

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self._triggers: list[str] = []
        self._routing: WakeWordRoutingConfig = WakeWordRoutingConfig()
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            data = json.loads(self.storage_path.read_text())
            self._triggers = data.get("triggers", WAKE_WORD_DEFAULTS)
            routing_data = data.get("routing")
            if routing_data:
                self._routing = WakeWordRoutingConfig(**routing_data)
        else:
            self._triggers = list(WAKE_WORD_DEFAULTS)

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps({
            "triggers": self._triggers,
            "routing": self._routing.__dict__,
        }, indent=2))

    def _normalize(self, triggers: list[str]) -> list[str]:
        """Trim whitespace, drop empty strings, enforce limits."""
        normalized = [t.strip().lower() for t in triggers if t.strip()]
        normalized = [t for t in normalized if len(t) <= WAKE_WORD_MAX_LENGTH]
        return normalized[:WAKE_WORD_MAX_COUNT] if normalized else list(WAKE_WORD_DEFAULTS)

    async def get(self) -> list[str]:
        return list(self._triggers)

    async def set(self, triggers: list[str]) -> list[str]:
        """
        Sets the trigger list. Normalizes, enforces limits, saves, and broadcasts to all nodes.
        Returns the normalized list that was actually saved.
        """
        self._triggers = self._normalize(triggers)
        self._save()
        await self._broadcast()
        return list(self._triggers)

    async def get_routing(self) -> "WakeWordRoutingConfig":
        return self._routing

    async def set_routing(self, config: "WakeWordRoutingConfig") -> "WakeWordRoutingConfig":
        self._routing = config
        self._save()
        await self._broadcast()
        return self._routing

    async def _broadcast(self) -> None:
        """Push the updated wake word list to all connected nodes via the node bus."""
        await node_bus.broadcast({
            "method": "voicewake.updated",
            "triggers": self._triggers,
            "routing": self._routing.__dict__,
        })


class WakeWordRoutingConfig:
    """
    Defines where a wake word activation is routed.
    Mirrors OpenClaw's VoiceWakeRoutingConfig shape for interoperability.
    """

    def __init__(
        self,
        version: int = 1,
        default_target: dict | None = None,
        device_targets: dict | None = None,
    ):
        self.version = version
        self.default_target = default_target or {"mode": "current"}
        # mode: "current" | "specific_node" | "active_session"
        # "current": activation goes to whichever node detected the wake word
        # "specific_node": always routes to a named node (e.g. the desktop app)
        # "active_session": routes to whichever session is currently active
        self.device_targets = device_targets or {}
        # Per-device overrides: { "node_id": { "mode": "..." } }
```

---

## Node Protocol

Nodes (desktop, mobile) communicate with the gateway using these methods. The gateway is authoritative; nodes are clients.

```
voicewake.get -> { triggers: string[] }
    Node requests the current trigger list.

voicewake.set { triggers: string[] } -> { triggers: string[] }
    Any node can update the list. Gateway normalizes and broadcasts.

voicewake.routing.get -> { config: WakeWordRoutingConfig }

voicewake.routing.set { config: WakeWordRoutingConfig } -> { config: WakeWordRoutingConfig }

voicewake.updated (server push) -> { triggers: string[], routing: WakeWordRoutingConfig }
    Broadcast from gateway to all connected nodes when the list changes.
    Nodes update their local detector immediately on receiving this.
```

The protocol is implemented over the existing node WebSocket bus. Message format matches the node bus message envelope already used for other gateway-to-node pushes.

---

## Per-Node Enable/Disable Toggle

Each node has a local toggle: voice wake enabled or disabled. This is a local preference (not shared to the gateway), because permission handling differs:

- **Desktop (macOS/Linux/Windows):** enable/disable via UI toggle in system tray or settings. Respects OS microphone permission. If permission is denied, the toggle shows as disabled with a note.
- **Mobile (iOS/Android):** enable/disable via app settings. iOS and Android handle microphone background permissions differently; the toggle reflects what the OS allows.
- **CLI/TUI:** no wake word detection (manual mic activation only).
- **Web app:** browser does not support background wake word detection; this feature is disabled in the web UI.

The gateway does not store per-node enable/disable state. Each node stores it locally.

```python
# Desktop app config (local, not synced):
{
    "voice_wake": {
        "enabled": true,          # user toggle
        "permission_granted": true  # OS-level, read-only
    }
}
```

---

## Wake Word Detector

The gateway does not do wake word detection itself. Detection runs on the node (the device with the microphone). The gateway owns the trigger list and receives activation events.

The detector is pluggable. In v1, two backends:

1. **OpenAI Whisper-based**: send a short rolling audio buffer to Whisper every 1-2 seconds, check if the transcript contains a trigger. Simple, uses existing Whisper integration (Prompt 27 / Prompt 47). Higher latency (~1s), higher cost if Whisper is cloud-hosted.

2. **Local keyword detector (pocketsphinx or Porcupine)**: runs entirely on-device with no API call. Zero cost, sub-100ms latency. Limited to a predefined vocabulary. Use this when available.

```python
# keprix/backend/voice/detector.py

class WakeWordDetector:
    """
    Wraps whichever local detection backend is available.
    Called by the desktop app node process, not by the gateway.
    """

    def __init__(self, triggers: list[str], backend: str = "whisper"):
        self.triggers = [t.lower() for t in triggers]
        self.backend = backend

    def update_triggers(self, triggers: list[str]) -> None:
        """Called when the gateway broadcasts a voicewake.updated event."""
        self.triggers = [t.lower() for t in triggers]
        if self.backend == "porcupine":
            self._reload_porcupine_keywords()

    def is_triggered(self, transcript: str) -> bool:
        """Returns True if any trigger phrase appears in the transcript."""
        text = transcript.lower().strip()
        return any(trigger in text for trigger in self.triggers)

    async def run_whisper_check(self, audio_bytes: bytes) -> bool:
        """
        Sends a short audio chunk to the STT provider (Prompt 47 / Prompt 27).
        Returns True if the transcript contains a trigger.
        Only used when backend == 'whisper'.
        """
        result = await stt_provider.transcribe(audio_bytes, language="en")
        return self.is_triggered(result.text)
```

---

## Activation Flow

When the detector fires:

1. Node sends `voicewake.triggered { node_id, trigger_phrase }` to the gateway.
2. Gateway routes the activation according to `WakeWordRoutingConfig`:
   - `mode: "current"`: gateway opens a new voice session on the triggering node.
   - `mode: "active_session"`: gateway routes to the currently active workspace session.
3. Gateway sends `voicewake.session_start { session_id }` back to the node.
4. Node opens the microphone in full recording mode (was in listening-only mode before).
5. User speaks; audio is streamed to the gateway.
6. Gateway sends audio through the STT + agent pipeline (Prompt 27, Prompt 47).
7. Response is returned via TTS to the node.
8. Node closes the microphone and returns to wake word listening mode.

---

## API Endpoints

```
GET    /api/voice/wake-words
       Returns: { triggers: string[], routing: WakeWordRoutingConfig }

PUT    /api/voice/wake-words
       Body: { triggers: string[] }
       Sets the trigger list. Broadcasts to all nodes.
       Returns: { triggers: string[] }  (normalized list)

GET    /api/voice/wake-words/routing
       Returns: WakeWordRoutingConfig

PUT    /api/voice/wake-words/routing
       Body: WakeWordRoutingConfig
       Returns: WakeWordRoutingConfig

POST   /api/voice/wake-words/reset
       Resets the trigger list to defaults (["keprix", "hey keprix"]).
```

---

## Settings UI

`/settings/voice/wake-words`

**Trigger list:** Editable list of trigger phrases. Add button. Delete button per phrase. Max 10 phrases shown. Character limit enforced in the input field.

**Default triggers shown:** "keprix" and "hey keprix". User can add custom triggers ("computer", "assistant", their own name, etc.).

**Save button:** calls `PUT /api/voice/wake-words`. On success, shows "Saved. Changes will take effect on all your connected devices."

**Routing section:** Radio buttons for routing mode ("Current device", "Always desktop", "Active session"). Only shown if the user has multiple connected nodes.

**Per-device status:** List of connected nodes with their local wake word status (enabled/disabled, permission granted/denied). Read-only; users change the toggle on the device itself.

---

## Acceptance Criteria

- `WakeWordRegistry.set(["Hey keprix", "computer", ""])` normalizes to `["hey keprix", "computer"]` (lowercase, empty dropped).
- Setting 11 triggers normalizes to 10 (max enforced).
- After `set()`, all connected nodes receive a `voicewake.updated` broadcast.
- `WakeWordDetector.is_triggered("hey keprix what time is it")` returns `True` when "hey keprix" is in the trigger list.
- `WakeWordDetector.is_triggered("hello, what time is it")` returns `False`.
- `update_triggers()` takes effect immediately: the next `is_triggered` call uses the new list.
- `POST /api/voice/wake-words/reset` restores `["keprix", "hey keprix"]` and broadcasts.
- `PUT /api/voice/wake-words` with an empty list restores defaults (does not set an empty trigger list).
- The storage file (`voicewake.json`) is written atomically (write to temp file, rename).
- The CLI and web app nodes correctly show wake word detection as unavailable/disabled.
- A node that was offline when triggers changed receives the updated list on its next `voicewake.get` call.
