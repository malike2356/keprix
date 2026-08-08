# Mobile apps

Native iOS and Android clients live under `mobile/ios` and `mobile/android`.
They connect to a self-hosted keprix backend, not a cloud service.

## Setup

1. Deploy or run your keprix backend (see installer docs).
2. On first launch, enter your server URL (for example `https://my-keprix.example.com`).
3. Pair the device from the workspace GUI at `/admin/companion` (Admin > Companion):
   create a pairing session, scan the QR or enter the short code, then confirm on device.
   Admins can also revoke paired devices from the same page.

API fallback (automation): `POST /api/companion/pair` still works for scripts, but the GUI is the primary operator path.

## API

Mobile clients use the same REST API as the web frontend:

- Auth: bearer token from companion pairing (stored in Keychain / EncryptedSharedPreferences)
- Inbox: `GET /api/notifications/inbox`
- Push registration: `POST /api/notifications/register`
- Health check: `GET /api/health`

## Paths

- iOS: `mobile/ios/` (Swift companion client)
- Android: `mobile/android/` (Kotlin companion client)
- macOS reference: `mobile/macos/`
- Companion pairing backend: `src/keprix/mobile/companion/`
- Push backend: `src/keprix/backend/notifications/push.py`

Until native builds are installed, the responsive web workspace at `/notifications` works on mobile browsers.
