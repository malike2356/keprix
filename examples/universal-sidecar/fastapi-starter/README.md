# FastAPI Universal Sidecar starter

Minimal product that talks to Keprix Universal Sidecar.

## Setup

```bash
cp .env.example .env
# start mock product or this app on :8099
# start sidecar on :3360 (or mounted :3333)
pip install fastapi uvicorn httpx python-dotenv
uvicorn main:app --host 127.0.0.1 --port 8099
```

Pair using a one-time code from Settings > Sidecars, then call health and
invoke via the SDK or curl examples.

Manifest: `keprix.sidecar.yaml`.
