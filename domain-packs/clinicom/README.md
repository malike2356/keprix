# Keprix Clinicom sidecar

Interim Keprix-compatible HTTP sidecar for [Clinicom AI](https://clinicomai.com). Exposes the `/clinicom/tools/*` contract Clinicom uses for speech, translation, simplification, and TTS.

Clinicom is a product surface; this pack implements the sidecar contract without duplicating Clinicom app code.

## Endpoints

| Method | Path | Tool |
| --- | --- | --- |
| GET | `/health` | Liveness probe |
| GET | `/clinicom/capabilities` | capability contract v2 |
| POST | `/clinicom/tools/transcribe` | `clinicom_transcribe` |
| POST | `/clinicom/tools/translate` | `clinicom_translate` |
| POST | `/clinicom/tools/simplify` | `clinicom_simplify` |
| POST | `/clinicom/tools/speak` | `clinicom_speak` |
| POST | `/clinicom/tools/cultural_adapt` | `clinicom_cultural_adapt` |
| POST | `/clinicom/tools/teachback_score` | `clinicom_teachback_score` |
| POST | `/clinicom/tools/safety_triage_assist` | `clinicom_safety_triage_assist` |
| POST | `/clinicom/tools/session_digest` | `clinicom_session_digest` |
| POST | `/clinicom/tools/specialty_simplify` | `clinicom_specialty_simplify` |
| POST | `/clinicom/tools/confidence_explain` | `clinicom_confidence_explain` |

Routes call `registry.dispatch()` on the pack-local tool registry. Handlers return JSON strings; HTTP routes parse and return objects.

## Run standalone (recommended for Clinicom)

From this directory:

```bash
cd /opt/lampp/htdocs/verlox/keprix/domain-packs/clinicom
python3 -m uvicorn http_app:app --host 0.0.0.0 --port 3353
```

Point Clinicom at the sidecar:

```bash
export CLINICOM_SIDECAR_PROFILE=keprix
export CLINICOM_KEPRIX_SIDECAR_URL=http://127.0.0.1:3353
export CLINICOM_SIDECAR_TOKEN=your-shared-token   # optional; must match CLINICOM_SHARED_TOKEN on the sidecar
```

Smoke from Clinicom repo root:

```bash
bash /opt/lampp/htdocs/verlox/clinicom-ai/scripts/smoke-sidecar.sh
```

## Provider wiring

Handlers resolve AI in this order:

1. `KEPRIX_ML_SERVICE_URL` (for example `http://127.0.0.1:8200`) for transcribe/translate/speak
2. `GEMINI_API_KEY` (or `KEPRIX_GEMINI_API_KEY` / `GOOGLE_API_KEY`) for translate, simplify, and audio transcribe
3. Deterministic stubs (`source: keprix-clinicom-stub`) when neither is available

From Clinicom:

```bash
bash /opt/lampp/htdocs/verlox/clinicom-ai/scripts/start-keprix-clinicom-sidecar.sh
```

That script starts this pack on port 3353 and loads the Hermes/Keprix Gemini key from `.access/.gemini-keys-31JUL2026.md` when present.

## Agent tools

Tool names registered in the pack registry:

- `clinicom_transcribe`
- `clinicom_translate`
- `clinicom_simplify`
- `clinicom_speak`
- `clinicom_cultural_adapt`
- `clinicom_teachback_score`
- `clinicom_safety_triage_assist`
- `clinicom_session_digest`
- `clinicom_specialty_simplify`
- `clinicom_confidence_explain`

## Contract v2

`/clinicom/capabilities` returns the active capability contract for the pack.

The contract marks each tool as one of:

- `live`
- `stub`
- `disabled`

Do not hide unavailable tools behind vague wording. Surface the actual state so the caller can make the right routing choice.

These mirror the Clinicom sidecar clone contract documented in `clinicom-ai/docs/sidecar-production.md`.

## Tests

From the Keprix repo root:

```bash
cd /opt/lampp/htdocs/verlox/keprix
pytest domain-packs/clinicom/tests/test_clinicom_sidecar.py -q
```

## Mounting into the main Keprix API

The main Keprix FastAPI app (`keprix.api.main:app`, port 3333) does not yet mount this pack router. Use the standalone sidecar above until a shared mount is added. Clinicom profiles should use a dedicated sidecar URL, not the general workspace API, unless routes are explicitly mounted.
