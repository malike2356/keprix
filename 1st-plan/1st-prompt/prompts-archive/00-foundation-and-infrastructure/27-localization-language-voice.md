# keprix - Prompt 27: Localization, Language Detection, Translation, And Voice

> **Status (2026-07-05):** Archived to `prompts-archive/`. Shipped: `backend/localization/` (detection, translation, transcription, speech, glossary, audit, preferences), Postgres dual-store (`migrations/versions/010_localization.py`), Telegram/WhatsApp gateway hooks (`backend/gateway/localization_hook.py`), `/language` slash command, `keprix language` CLI, `examples/borehole-ghana/`, 46 localization tests.

## Purpose

Add a first-class localization and language layer to keprix so products built on keprix can serve users in their local language through text, speech, and channel-native output.

This is a core platform capability, not a single app feature. A borehole drilling app in Ghana, a local clinic assistant in Kenya, a farm advisory tool in Nigeria, a delivery workflow in South Africa, or a municipal support bot in Senegal should be able to detect user language, understand speech, translate intent safely, answer in the right language, and preserve domain terms through playbooks.

## Scope

Implement:

- Language detection for text and speech.
- Translation into and out of the workspace operating language.
- Transcription for voice notes, calls, uploaded audio, and channel voice messages.
- Text-to-speech for local-language replies where reliable voices exist.
- Per-user and per-channel language preferences.
- Domain glossaries for specialist products such as borehole drilling, agriculture, healthcare, legal support, finance, and education.
- Localized playbooks, prompts, labels, error messages, and command responses.
- Provider routing for cloud and local language services.
- Human review hooks for low-confidence translations.
- Audit records that preserve original text, translated text, detected language, confidence, provider, and safety flags.
- Tests for multilingual text, speech, fallback behavior, glossary protection, and channel formatting.

## Product Direction

keprix should treat language as part of the workspace runtime:

- Users speak or type naturally.
- keprix detects the language and dialect where possible.
- keprix converts the user request into a stable internal representation.
- Tools and playbooks operate on structured intent, not brittle translated text only.
- keprix replies in the user's preferred language and format.
- Voice output is available when the channel supports it.
- Operators can review language quality, glossary conflicts, and safety issues.

Start with a practical African language coverage plan, not a Ghana-only list. Support should be tiered by demand, provider quality, available speech models, and product market.

Priority African language groups for v1:

- West Africa: Akan/Twi, Fante, Ga, Ewe, Hausa, Yoruba, Igbo, Fulfulde, Wolof, Mandinka, Bambara, Moore, Dagbani, Nzema, Krobo, and Nigerian Pidgin.
- East Africa: Swahili, Amharic, Oromo, Somali, Tigrinya, Kinyarwanda, Kirundi, Luganda, Luo, Kikuyu, and Kalenjin.
- Southern Africa: Zulu, Xhosa, Afrikaans, Sesotho, Setswana, Sepedi, Venda, Tsonga, Shona, Ndebele, Chichewa, and Portuguese for Mozambique and Angola.
- Central Africa: Lingala, Kikongo, Tshiluba, Sango, Kinyarwanda, Kirundi, French regional variants, and local Arabic variants where applicable.
- North Africa: Arabic regional variants, Egyptian Arabic, Moroccan Darija, Algerian Arabic, Tunisian Arabic, Sudanese Arabic, Tamazight, Tachelhit, Tarifit, Kabyle, and French regional variants.

Keep the system extensible for country-specific languages and dialects as models, community data, and customer demand improve. Do not pretend every language has equal model quality. The runtime must expose confidence, fallback behavior, and human review paths.

## Output Paths

Use these target paths unless the codebase evolves before implementation:

```text
keprix/backend/localization/
  __init__.py
  detection.py
  translation.py
  transcription.py
  speech.py
  preferences.py
  glossary.py
  confidence.py
  audit.py
  schemas.py
  providers/
    __init__.py
    base.py
    local.py
    cloud.py
    openai.py
    google.py
    azure.py
    whisper.py

keprix/backend/playbook/localization.py
keprix/backend/gateway/language_middleware.py
keprix/backend/api/localization.py
keprix/tests/localization/
keprix/examples/borehole-ghana/
```

## Language Contract

Create typed models for all language operations:

```python
class LanguageDetectionResult:
    language_code: str
    language_name: str
    script: str | None
    region: str | None
    confidence: float
    alternatives: list[LanguageCandidate]
    provider: str

class TranslationRequest:
    workspace_id: str
    source_language: str | None
    target_language: str
    text: str
    domain: str | None
    glossary_id: str | None
    preserve_terms: list[str]
    user_id: str | None

class TranslationResult:
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    confidence: float
    glossary_matches: list[str]
    warnings: list[str]
    provider: str

class TranscriptionResult:
    language_code: str
    transcript: str
    confidence: float
    segments: list[TranscriptSegment]
    provider: str

class SpeechSynthesisResult:
    language_code: str
    voice_id: str
    audio_url: str
    transcript: str
    provider: str
```

Use BCP 47 language codes where possible, for example `en-GB`, `en-GH`, `ak-GH`, `tw-GH`, `gaa-GH`, `ee-GH`, `ha-NG`, `yo-NG`, `ig-NG`, `sw-KE`, `am-ET`, `so-SO`, `rw-RW`, `zu-ZA`, `xh-ZA`, `st-ZA`, `tn-BW`, `sn-ZW`, `ny-MW`, `ln-CD`, `ar-EG`, `ary-MA`, and `kab-DZ`. If a provider lacks a canonical code for a local language or dialect, map it through an internal alias table and keep the original provider label in metadata.

## African Language Coverage

Create a language catalog that groups languages by country, region, script, provider support, speech support, and confidence expectations.

Each language entry must support:

- Canonical language code.
- Display name.
- Local display name where known.
- Countries and regions where it is commonly used.
- Script.
- Direction, such as left-to-right or right-to-left.
- Text detection support.
- Translation support.
- Speech-to-text support.
- Text-to-speech support.
- Recommended providers.
- Minimum confidence threshold.
- Whether human review is required by default.
- Known dialect aliases.
- Fallback languages.

Example catalog entry:

```yaml
- code: sw-KE
  name: Swahili
  local_name: Kiswahili
  regions:
    - Kenya
    - Tanzania
    - Uganda
    - Rwanda
    - Democratic Republic of the Congo
  script: Latin
  direction: ltr
  text_detection: supported
  translation: supported
  speech_to_text: supported
  text_to_speech: supported
  fallback_languages:
    - en-KE
    - en
  human_review_default: false
```

The initial catalog should include at least:

| Region | Languages |
| --- | --- |
| Ghana and nearby markets | Akan/Twi, Fante, Ga, Ewe, Hausa, Dagbani, Nzema, Krobo |
| Nigeria | Hausa, Yoruba, Igbo, Fulfulde, Kanuri, Tiv, Edo, Ibibio, Nigerian Pidgin |
| Francophone West Africa | Wolof, Bambara, Mandinka, Moore, Fulfulde, French regional variants |
| East Africa | Swahili, Amharic, Oromo, Somali, Tigrinya, Luganda, Luo, Kikuyu, Kinyarwanda, Kirundi |
| Southern Africa | Zulu, Xhosa, Sesotho, Setswana, Sepedi, Venda, Tsonga, Shona, Ndebele, Chichewa, Afrikaans |
| Central Africa | Lingala, Kikongo, Tshiluba, Sango, Kinyarwanda, Kirundi |
| North Africa | Arabic regional variants, Egyptian Arabic, Moroccan Darija, Algerian Arabic, Tunisian Arabic, Tamazight, Tachelhit, Tarifit, Kabyle |

For low-resource languages, support can start with detection, guided intake, bilingual responses, and human review before full automated translation or voice output is enabled.

## Runtime Flow

For every inbound message:

1. Capture the original input without altering it.
2. If the input is audio, transcribe it and detect the spoken language.
3. If the input is text, detect the language directly.
4. Resolve the user's preferred output language from explicit preference, channel setting, prior behavior, then workspace default.
5. Translate into the workspace operating language if needed.
6. Extract intent and entities from the translated text and the original text.
7. Run tools, playbooks, or agent reasoning on structured intent.
8. Generate the answer in the workspace operating language.
9. Translate the answer into the user's preferred output language.
10. Apply glossary and domain term checks.
11. Return text, audio, or both depending on user preference and channel capability.
12. Write the localization audit record.

Never discard the original language input. It is needed for dispute resolution, human review, improving domain glossaries, and checking whether the translation changed the user's intent.

## Provider Routing

Create a provider router that can choose between local and cloud services:

| Capability | Preferred First Pass | Fallback |
| --- | --- | --- |
| Text language detection | Local fast detector | Cloud detector |
| Speech transcription | Local Whisper-compatible model | Cloud speech-to-text |
| Translation | Cloud translator for low-resource languages | Local model where quality is proven |
| Text-to-speech | Cloud voices for local languages | Local TTS where available |
| Glossary enforcement | keprix local glossary layer | Human review |

Provider selection must consider:

- Workspace privacy policy.
- Offline mode.
- Cost limits.
- Language support.
- Confidence.
- Latency.
- Whether the user has allowed cloud processing.

If cloud processing is disabled, clearly return that a reliable translation or voice output is unavailable instead of silently producing a weak answer.

## Domain Glossaries

Build a glossary service so apps can protect specialist meaning.

Glossary entries must support:

- Source term.
- Local-language equivalent.
- Approved English equivalent.
- Domain.
- Notes.
- Forbidden translations.
- Example usage.
- Review status.
- Last reviewer.

Example for a Ghana borehole drilling product:

```json
{
  "domain": "borehole_drilling",
  "entries": [
    {
      "term": "yield test",
      "approved_equivalent": "yield test",
      "notes": "Do not translate as crop yield. This means water output from a borehole."
    },
    {
      "term": "casing",
      "approved_equivalent": "borehole casing",
      "notes": "Protect as a technical drilling component."
    },
    {
      "term": "aquifer",
      "approved_equivalent": "underground water-bearing layer",
      "notes": "Use a simple explanation when no trusted local equivalent exists."
    }
  ]
}
```

The glossary layer must run before and after translation. Before translation, it identifies protected terms. After translation, it checks that protected meaning survived.

## Localized Playbooks

Playbooks must be localization-aware:

- A playbook can declare supported languages.
- A playbook can attach a glossary.
- A playbook can define local safety warnings.
- A playbook can specify when to answer bilingually.
- A playbook can require human review below a confidence threshold.

Example playbook metadata:

```yaml
id: ghana-borehole-advisor
domain: borehole_drilling
workspace_language: en-GH
supported_input_languages:
  - en-GH
  - ak-GH
  - tw-GH
  - gaa-GH
  - ee-GH
default_output_mode: text_and_voice_when_available
glossary_id: borehole_drilling_ghana_v1
human_review_below_confidence: 0.72
```

Localized playbooks should not duplicate all business logic per language. Keep one canonical workflow and localize prompts, labels, examples, warnings, and output templates around it.

## User Preferences

Store language preferences per user and workspace:

```sql
CREATE TABLE user_language_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    preferred_input_language TEXT,
    preferred_output_language TEXT,
    voice_output_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    preferred_voice_id TEXT,
    bilingual_replies BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, user_id)
);
```

Support explicit commands:

- `/language`
- `/language set tw-GH`
- `/language voice on`
- `/language bilingual on`
- `/language reset`

Prompt 23 owns the slash command registry. This prompt adds the language command handlers and metadata.

## Channel Behavior

### Telegram And WhatsApp-Style Channels

- Accept voice notes.
- Reply with text by default.
- Send audio reply only when the user enabled voice output or the app requires voice.
- Keep replies short for low-literacy or field-worker scenarios.
- Use buttons for language selection where supported.

### WebChat

- Offer a language selector.
- Show original and translated text in operator review mode.
- Support audio upload and playback.
- Show confidence warnings without exposing technical provider details to end users.

### CLI And TUI

- Support `keprix language detect`, `keprix translate`, and `keprix transcribe`.
- Keep voice output optional.
- Print language code, confidence, and provider in diagnostic mode.

## Human Review

Low-resource language support can fail in subtle ways. Add review hooks when:

- Detection confidence is below threshold.
- Translation confidence is below threshold.
- Glossary checks fail.
- A regulated domain is active, such as healthcare, legal, finance, safety, or construction.
- The user disputes an answer.
- The request may trigger an external action or paid action.

Review records must include the original input, transcription, translation, final answer, language codes, provider names, confidence scores, glossary warnings, and reviewer decision.

## Audit Log

Create a localization audit table:

```sql
CREATE TABLE localization_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    user_id TEXT,
    channel TEXT NOT NULL,
    request_id TEXT NOT NULL,
    input_type TEXT NOT NULL,
    detected_language TEXT,
    output_language TEXT,
    detection_confidence DOUBLE PRECISION,
    transcription_provider TEXT,
    translation_provider TEXT,
    speech_provider TEXT,
    glossary_id TEXT,
    glossary_warnings JSONB DEFAULT '[]',
    human_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Do not store raw audio forever by default. Store transcripts and short-lived audio references according to workspace retention policy.

## API Surface

Expose:

```text
POST /api/localization/detect
POST /api/localization/translate
POST /api/localization/transcribe
POST /api/localization/speech
GET  /api/localization/languages
GET  /api/localization/preferences
POST /api/localization/preferences
GET  /api/localization/glossaries
POST /api/localization/glossaries
GET  /api/localization/audit
```

All endpoints require authentication except channel webhooks that have already passed platform signature verification.

## Configuration

Add workspace configuration:

```yaml
localization:
  enabled: true
  workspace_language: en-GH
  default_output_language: en-GH
  allowed_cloud_processing: true
  default_voice_output: false
  human_review_below_confidence: 0.72
  supported_languages:
    - en-GH
    - ak-GH
    - tw-GH
    - gaa-GH
    - ee-GH
    - ha-NG
    - yo-NG
    - ig-NG
    - pcm-NG
    - wo-SN
    - bm-ML
    - sw-KE
    - sw-TZ
    - am-ET
    - om-ET
    - so-SO
    - rw-RW
    - zu-ZA
    - xh-ZA
    - st-ZA
    - tn-BW
    - sn-ZW
    - ny-MW
    - ln-CD
    - ar-EG
    - ary-MA
    - kab-DZ
  providers:
    detection:
      primary: local
      fallback: cloud
    transcription:
      primary: whisper
      fallback: cloud
    translation:
      primary: cloud
      fallback: local
    speech:
      primary: cloud
      fallback: none
```

## Ghana Borehole Example

Build a small example app under `examples/borehole-ghana/`:

- User sends a Twi voice note asking whether a location is suitable for a borehole.
- keprix transcribes the voice note.
- keprix detects Twi or Akan with confidence.
- keprix translates the request into English Ghana operating language.
- keprix uses a borehole drilling playbook and glossary.
- keprix asks for missing fields: community, GPS location, soil type if known, nearby wells, expected household count, and budget range.
- keprix replies in Twi text and optional audio.
- Operator review mode shows original audio transcript, English translation, tool actions, and final local-language response.

The example must make clear that keprix is not replacing a licensed hydrogeologist. It can collect intake, explain next steps, and route the job to a qualified professional.

## Tests

Add tests for:

- Text language detection returns a language code and confidence.
- Audio transcription preserves timestamps and detected language.
- User preference overrides workspace default language.
- Unknown language falls back to workspace language with a clear warning.
- Translation protects glossary terms.
- Borehole glossary prevents wrong translation of "yield test".
- Low confidence translation creates a human review task.
- Voice output is skipped when the channel does not support audio.
- Voice output is skipped when user preference is disabled.
- Cloud provider is blocked when workspace policy disables cloud processing.
- `/language set tw-GH` updates the user's output preference.
- `/language set sw-KE` updates the user's output preference.
- `/language set yo-NG` updates the user's output preference.
- `/language voice on` enables speech output only for the current user.
- Localization audit records provider, confidence, and glossary warnings.
- Original input is preserved in review mode.

## Acceptance Criteria

- keprix can detect language for inbound text messages.
- keprix can transcribe a voice note and pass the transcript through normal agent intent handling.
- keprix can translate user input into the workspace operating language and translate the final response back to the user's preferred language.
- keprix supports text output and optional audio output.
- keprix stores per-user language preferences.
- keprix exposes language slash commands through the Prompt 23 registry.
- keprix supports domain glossaries and localized playbooks.
- keprix ships an African language catalog covering priority languages across West, East, Southern, Central, and North Africa.
- keprix marks low-resource languages with confidence thresholds, fallback languages, and human review defaults.
- The Ghana borehole example demonstrates Twi/Akan, Ga, or Ewe text input and at least one voice-note flow.
- Low-confidence or regulated-domain translations can be routed for human review.
- Audit records exist for detection, transcription, translation, glossary warnings, and speech synthesis.
