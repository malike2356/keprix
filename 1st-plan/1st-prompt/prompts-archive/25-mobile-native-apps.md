# keprix - Prompt 25: Mobile Native Apps (iOS and Android)

## Context

Source: `openclaw/apps/ios/` (Swift), `openclaw/apps/android/` (Kotlin)
Output: `keprix/mobile/ios/`, `keprix/mobile/android/`

This prompt ports the OpenClaw iOS and Android native apps to keprix.
The apps connect to the user's self-hosted keprix backend.

## Critical: Connection Model Change

OpenClaw apps connect to openclaw.ai cloud. keprix apps connect to the
user's own backend. Every hardcoded URL, API endpoint, and service reference
must change from OpenClaw's hosted service to a user-configured server URL.

The apps must allow the user to set their keprix server URL at first launch
(e.g. `https://my-carina.example.com`). This is stored in Keychain/EncryptedSharedPreferences.

## iOS App Port

### Source: `openclaw/apps/ios/`

Port every Swift file verbatim, then apply targeted changes:

1. **Copy the entire `apps/ios/` tree to `keprix/mobile/ios/`**

2. **Rename app identifiers**:
   - Bundle ID: `com.openclaw.app` -> `com.verlox.carinakeprix`
   - App name: `OpenClaw` -> `keprix`
   - All `OpenClaw*` class/struct/file names -> `Carina*`
     e.g. `OpenClawApp.swift` -> `CarinaApp.swift`
     e.g. `OpenClawActivityWidgetBundle.swift` -> `CarinaActivityWidgetBundle.swift`

3. **Update API endpoints** in all Swift files:
   - Remove any hardcoded `openclaw.ai` URLs
   - Replace with `CarinaServerConfig.serverURL` (read from user settings)
   - Implement `CarinaServerConfig.swift` that reads/writes server URL from Keychain

4. **First-launch onboarding screen** `CarinaOnboardingView.swift`:
   - Text field: "Enter your keprix server URL"
   - Validation: must be a valid HTTPS URL (or allow HTTP for local dev)
   - Test connection button: pings `{serverURL}/api/health`
   - On success: save URL to Keychain, navigate to main app

5. **Preserve all existing OpenClaw features**:
   - Tab navigation (`RootTabs.swift`, `RootTabsNavigation.swift`)
   - Session management (`SessionKey.swift`)
   - Share Extension (`ShareExtension/ShareViewController.swift`) - share to Carina
   - Live Activity widget (`ActivityWidget/`) - show agent status on Lock Screen
   - Background alive beacon (`Tests/BackgroundAliveBeaconTests.swift` reference)
   - Camera integration (camera controller clamp/error - see tests)
   - Command Center tab (session filter, layout - see tests)
   - Deep link handling (`Tests/DeepLinkParserTests.swift` reference)
   - Gateway connection controller (see `Tests/GatewayConnectionControllerTests.swift`)
   - Push notification bridge for exec approval

6. **Voice features** (preserve from OpenClaw):
   - Speech-to-text via Whisper (local or cloud)
   - Text-to-speech: macOS MLX TTS bridge for on-device TTS
   - Voice memo recording

7. **Update project.yml**: app name, bundle ID, team (leave as placeholder `DEVELOPMENT_TEAM`)

8. **Update signing config** `Config/Signing.xcconfig`:
   - `PRODUCT_BUNDLE_IDENTIFIER = com.verlox.carinakeprix`
   - Leave `DEVELOPMENT_TEAM` as empty placeholder

### iOS Build Verification (do not run, just verify files exist):

After port, confirm these files exist:
- `keprix/mobile/ios/Sources/CarinaApp.swift`
- `keprix/mobile/ios/Sources/CarinaOnboardingView.swift` (new file)
- `keprix/mobile/ios/Sources/CarinaServerConfig.swift` (new file)
- `keprix/mobile/ios/project.yml`
- `keprix/mobile/ios/Sources/RootTabs.swift`

## Android App Port

### Source: `openclaw/apps/android/`

Port every Kotlin/Gradle file verbatim, then apply targeted changes:

1. **Copy the entire `apps/android/` tree to `keprix/mobile/android/`**

2. **Rename app identifiers**:
   - Application ID: `com.openclaw` -> `com.verlox.carinakeprix`
   - App name in `strings.xml`: `OpenClaw` -> `keprix`
   - All `OpenClaw*` class names -> `Carina*`

3. **Update API endpoints**:
   - Remove hardcoded `openclaw.ai` URLs
   - Create `CarinaServerConfig.kt` using `EncryptedSharedPreferences`
   - Server URL stored encrypted at rest

4. **First-launch onboarding Activity** `CarinaOnboardingActivity.kt`:
   - EditText for server URL
   - "Test Connection" button - HTTP GET to `{url}/api/health`
   - On success: save URL to EncryptedSharedPreferences, launch MainActivity

5. **Preserve all existing OpenClaw Android features**:
   - App structure (`app/build.gradle.kts`, `settings.gradle.kts`)
   - Proguard rules (`proguard-rules.pro`)
   - Benchmark suite (`benchmark/build.gradle.kts`)
   - Performance scripts (`scripts/perf-startup-benchmark.sh`, `perf-startup-hotspots.sh`)
   - Voice E2E script (`scripts/voice-e2e.sh`)
   - Startup performance benchmark (`perf-online-benchmark.sh`)
   - Lint rules (`lint.xml`)
   - Build release AAB script (`scripts/build-release-aab.ts`)
   - All dependency versions from `gradle/libs.versions.toml`

6. **Voice features** (preserve):
   - STT via device microphone + Whisper API
   - TTS via Android TTS engine or ElevenLabs

7. **Rename in build files**:
   - `app/build.gradle.kts`: update `applicationId`
   - `settings.gradle.kts`: update root project name
   - `gradle.properties`: update any openclaw-specific entries

### Android Build Verification (do not run, just verify files exist):

After port, confirm these files exist:
- `keprix/mobile/android/app/build.gradle.kts`
- `keprix/mobile/android/app/src/main/kotlin/com/verlox/carinakeprix/CarinaOnboardingActivity.kt` (new)
- `keprix/mobile/android/app/src/main/kotlin/com/verlox/carinakeprix/CarinaServerConfig.kt` (new)
- `keprix/mobile/android/settings.gradle.kts`

## Companion Pairing (from Odysseus)

Port `odysseus/companion/` to `keprix/mobile/companion/`:
```
companion/pairing.py   -> mobile/companion/pairing.py
companion/routes.py    -> mobile/companion/routes.py
```

This enables device pairing between mobile apps and the backend server:
- `POST /api/companion/pair` - initiate pairing (returns QR code data)
- `POST /api/companion/pair/confirm` - confirm pairing with code
- `GET /api/companion/paired` - list paired devices
- `DELETE /api/companion/paired/{id}` - unpair device

The mobile apps implement a QR-code scanner to pair with the backend.
Pairing issues a device token stored on the mobile device and verified by
the backend on every request.

## macOS App Reference

OpenClaw has a macOS app at `openclaw/apps/macos/`. Copy the directory to
`keprix/mobile/macos/` with the same rename rules applied, then complete the
desktop shell so it can connect to the Keprix backend. The macOS MLX TTS is
already ported in Prompt 04.

## Windows Companion

OpenClaw has a Windows Hub (`openclaw/apps/` if present). Port any Windows
companion app to `keprix/mobile/windows/` with same rename rules.
If the upstream folder is missing, create a minimal Windows companion shell
with the same backend connection, authentication, notification, and update
checks used by the other clients.

## Push Notifications

Both iOS and Android apps must support push notifications for:
- New incoming message on a connected channel
- Agent task completion
- Deep Research job complete
- Calendar reminder

Use Firebase Cloud Messaging (FCM) for Android and APNs for iOS.
The backend sends pushes via `backend/notifications/push.py`:
- `POST /api/notifications/register` - register device push token
- `POST /api/notifications/send` (internal) - send push from backend

## App API Contract

The mobile apps use the same REST API as the web frontend. All endpoints prefixed
`/api/`. Auth via bearer token stored in Keychain/EncryptedSharedPreferences.
The companion pairing flow issues this bearer token.

## Acceptance Criteria

- `keprix/mobile/ios/Sources/CarinaApp.swift` exists and contains "Carina" not "OpenClaw"
- `keprix/mobile/android/app/build.gradle.kts` has `applicationId = "com.verlox.carinakeprix"`
- `grep -r "openclaw.ai" keprix/mobile/` returns zero matches
- `grep -r "OpenClaw" keprix/mobile/ios/Sources/` returns zero matches in code (only allowed in LICENSE comments)
- `CarinaOnboardingView.swift` and `CarinaOnboardingActivity.kt` exist with server URL input
- `CarinaServerConfig` implementations exist in both iOS and Android
- Companion pairing route responds to `POST /api/companion/pair` with a QR payload
