# keprix - Prompt 49: Voice Template System

## Context

Read `35-localization-language-voice.md` and `93-african-language-provider-adapters.md` first.

Prompt 27 specified TTS output using cloud providers and SeamlessM4T. Prompt 47 added SeamlessM4T as the primary TTS provider for African languages. The honest problem with both: TTS quality for Twi, Ewe, Ga, Dagbani, and most Ghanaian languages is rough in 2025. The models can produce intelligible speech, but a field contractor using AbbiS in Ashanti Region will notice unnatural rhythm, wrong tones, and awkward sentence stress immediately. Low-quality voice output destroys trust faster than no voice output.

This prompt builds a pragmatic bridge: a voice template system that serves pre-recorded audio for common, predictable responses, and falls back to TTS only for dynamic content that cannot be predicted in advance. In a typical borehole advisory conversation, 70-80% of the agent's utterances are standard responses: greetings, confirmations, requests for missing information, status messages, completion announcements. These can be recorded by a native speaker once and served with zero quality compromise indefinitely.

The template system does not replace TTS. It wraps it. When a matching template exists, serve the recording. When no template matches or the response is dynamic (contains a price, a GPS coordinate, a specific location name), fall back to SeamlessM4T or cloud TTS for the dynamic portion. A common pattern is template + TTS hybrid: play a recorded phrase for the standard part, then append synthesised audio for the variable part.

---

## File Structure

```
keprix/backend/voice_templates/
    __init__.py
    library.py          - template library: storage, lookup, matching
    player.py           - template serving and TTS hybrid assembly
    approval.py         - upload and approval workflow
    schemas.py          - typed models
    routes.py           - API endpoints

keprix/tests/voice_templates/
    test_library.py
    test_player.py
    test_approval.py

keprix/ui/web/src/app/(workspace)/settings/voice-templates/
    page.tsx            - template management UI for operators
    upload/page.tsx     - upload and recording form
    [id]/page.tsx       - template detail and approval view
```

---

## Database

```sql
CREATE TABLE voice_template_categories (
    id TEXT PRIMARY KEY,
    -- snake_case category code, e.g. 'greeting', 'ask_for_location'
    label TEXT NOT NULL,
    -- human-readable label for the management UI
    description TEXT,
    domain TEXT NOT NULL DEFAULT 'generic',
    -- 'generic' for built-in categories; domain name for domain pack categories
    is_dynamic BOOLEAN NOT NULL DEFAULT FALSE,
    -- if true, this category expects dynamic content to be appended via TTS
    dynamic_placeholder TEXT,
    -- the variable portion, e.g. '{price}' or '{location}'; inserted after template audio
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE voice_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id TEXT NOT NULL REFERENCES voice_template_categories(id),
    language_code TEXT NOT NULL,
    -- BCP 47 code, e.g. 'ak-GH', 'ee-GH', 'gaa-GH'
    dialect_note TEXT,
    -- optional human note about dialect variant, e.g. 'Asante Twi' vs 'Akuapem Twi'
    audio_file_id UUID NOT NULL,
    -- reference to workspace file store (Prompt 10)
    transcript TEXT NOT NULL,
    -- what the recording says, in the native language
    transcript_english TEXT NOT NULL,
    -- English translation of the transcript
    duration_seconds FLOAT NOT NULL,
    recorded_by TEXT,
    -- name of the native speaker who recorded this
    recorded_at DATE,
    quality_rating SMALLINT,
    -- 1-5 stars; set by operator after review
    status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'approved', 'rejected', 'archived'
    approved_by_user_id UUID,
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    play_count BIGINT NOT NULL DEFAULT 0,
    workspace_id UUID,
    -- null for system-wide templates; UUID for workspace-specific overrides
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (category_id, language_code, workspace_id)
    -- one approved template per category/language/workspace combination
);

CREATE INDEX ON voice_templates(category_id, language_code, status);
CREATE INDEX ON voice_templates(workspace_id, status);
```

---

## Built-In Template Categories

Seeded into `voice_template_categories` at startup. These are domain `generic`:

| Category ID | Label | Dynamic? | Description |
|---|---|---|---|
| `greeting` | Greeting | No | Opening greeting at start of conversation |
| `confirm_received` | Acknowledged | No | Confirm user's message was understood |
| `processing` | Processing | No | Agent is working, please wait |
| `response_ready` | Answer ready | No | About to give the answer |
| `ask_for_clarification` | Needs clarification | No | Need the user to rephrase or add detail |
| `low_confidence` | Low confidence | No | Not confident in the answer, suggesting English or human |
| `missing_info_prompt` | Missing information | No | A required detail was not provided (follow-up prompt in text; voice just introduces it) |
| `confirmation_success` | Done | No | Action completed successfully |
| `error_occurred` | Error | No | Something went wrong |
| `transfer_to_human` | Transferring | No | Routing to a human operator |
| `farewell` | Goodbye | No | Closing the conversation |
| `voice_not_available` | Voice unavailable | No | Tells user this language has no voice output yet; answer is in text |

Domain packs register additional categories. The `borehole-africa` pack (Prompt 24) adds:

| Category ID | Label | Dynamic? | Placeholder |
|---|---|---|---|
| `ask_for_location` | Ask for location | No | |
| `ask_for_depth` | Ask for depth | No | |
| `ask_for_community_size` | Ask for community size | No | |
| `quote_calculating` | Calculating quote | No | |
| `quote_ready` | Quote ready - price | Yes | `{price}` |
| `cwsa_compliant` | CWSA compliant | No | |
| `cwsa_not_compliant` | CWSA issue found | Yes | `{issue}` |
| `geology_assessment` | Geology info | Yes | `{geology_note}` |
| `technician_scheduled` | Technician visit scheduled | Yes | `{date}` |

---

## Template Library

```python
# keprix/backend/voice_templates/library.py

class VoiceTemplateLibrary:

    def has_templates(self, language_code: str) -> bool:
        """Returns True if any approved templates exist for this language."""
        return bool(self._get_approved_count(language_code))

    async def get_template(
        self,
        category_id: str,
        language_code: str,
        workspace_id: str | None = None,
    ) -> VoiceTemplate | None:
        """
        Returns the best matching template:
        1. Workspace-specific approved template for this category + language.
        2. System-wide approved template for this category + language.
        3. Fallback language: try primary language (e.g. 'ak-GH' for 'fan-GH' Fante).
        4. None if no match.
        """
        # Try workspace-specific first
        template = await db.fetchone(
            """SELECT * FROM voice_templates
               WHERE category_id = $1 AND language_code = $2
               AND workspace_id = $3 AND status = 'approved'""",
            category_id, language_code, workspace_id,
        )
        if template:
            return VoiceTemplate(**template)

        # Try system-wide
        template = await db.fetchone(
            """SELECT * FROM voice_templates
               WHERE category_id = $1 AND language_code = $2
               AND workspace_id IS NULL AND status = 'approved'""",
            category_id, language_code,
        )
        if template:
            return VoiceTemplate(**template)

        # Try fallback language
        fallback = LANGUAGE_FALLBACKS.get(language_code)
        if fallback:
            return await self.get_template(category_id, fallback, workspace_id)

        return None

    async def get_languages_with_coverage(self) -> dict[str, dict]:
        """
        Returns {language_code: {total_categories, covered_categories, coverage_pct}}.
        Used in the management UI to show which languages are well-covered.
        """

    async def increment_play_count(self, template_id: UUID) -> None:
        await db.execute("UPDATE voice_templates SET play_count = play_count + 1 WHERE id = $1",
                         template_id)
```

---

## Voice Player

The player assembles the final audio response. It handles four cases:

1. **Pure template:** response maps to a non-dynamic category, template exists. Return template audio directly.
2. **Template + TTS hybrid:** response is dynamic, template exists for the introduction, TTS handles the variable part. Concatenate audio.
3. **Pure TTS:** no matching template. Fall back to SeamlessM4T or cloud TTS for the full response.
4. **Text only:** TTS quality is unacceptable for this language or voice output is disabled. Return text with a note.

```python
# keprix/backend/voice_templates/player.py

class VoicePlayer:

    async def assemble_response(
        self,
        category_id: str,
        language_code: str,
        dynamic_text: str | None,
        full_text_fallback: str,
        workspace_id: str,
    ) -> VoiceResponseAssembly:
        """
        Returns an assembled audio response plus a transcript.

        VoiceResponseAssembly:
          audio_url: str | None        - URL of assembled audio; None if text-only
          transcript: str              - full text of what was said/shown
          method: str                  - 'template', 'template_tts_hybrid', 'tts', 'text_only'
          template_id: UUID | None
        """
        template = await template_library.get_template(category_id, language_code, workspace_id)

        if template and not is_dynamic_category(category_id):
            # Case 1: pure template
            await template_library.increment_play_count(template.id)
            return VoiceResponseAssembly(
                audio_url=await file_store.get_url(template.audio_file_id),
                transcript=template.transcript,
                method="template",
                template_id=template.id,
            )

        if template and is_dynamic_category(category_id) and dynamic_text:
            # Case 2: template intro + TTS for the dynamic part
            template_audio = await file_store.get_bytes(template.audio_file_id)
            dynamic_audio = await tts_provider.synthesize(
                text=dynamic_text,
                language=language_code,
            )
            combined_audio = concatenate_audio(template_audio, dynamic_audio, gap_ms=400)
            combined_url = await file_store.save_temp_audio(combined_audio, language_code)
            await template_library.increment_play_count(template.id)
            return VoiceResponseAssembly(
                audio_url=combined_url,
                transcript=template.transcript + " " + dynamic_text,
                method="template_tts_hybrid",
                template_id=template.id,
            )

        if tts_provider.supports(language_code):
            # Case 3: pure TTS
            audio = await tts_provider.synthesize(full_text_fallback, language_code)
            audio_url = await file_store.save_temp_audio(audio, language_code)
            return VoiceResponseAssembly(
                audio_url=audio_url,
                transcript=full_text_fallback,
                method="tts",
                template_id=None,
            )

        # Case 4: text only
        return VoiceResponseAssembly(
            audio_url=None,
            transcript=full_text_fallback,
            method="text_only",
            template_id=None,
        )
```

Audio concatenation uses `pydub` or a simple WAV byte-level append (both audio clips must be normalised to the same sample rate and format before concatenation - 16kHz, 16-bit mono is the target format):

```python
def concatenate_audio(audio1: bytes, audio2: bytes, gap_ms: int = 400) -> bytes:
    """
    Concatenate two WAV audio clips with a silence gap between them.
    Both clips must be 16kHz 16-bit mono WAV.
    """
    silence = generate_silence_wav(gap_ms, sample_rate=16000)
    return combine_wav_bytes([audio1, silence, audio2])
```

---

## Approval Workflow

Templates uploaded by operators go through a review step before serving. This prevents low-quality or incorrect recordings from reaching users.

States: `pending` -> `approved` or `rejected` -> optionally `archived`

```python
# keprix/backend/voice_templates/approval.py

async def submit_template(
    workspace_id: str,
    category_id: str,
    language_code: str,
    audio_bytes: bytes,
    transcript: str,
    transcript_english: str,
    recorded_by: str,
    recorded_at: date,
    dialect_note: str | None = None,
) -> VoiceTemplate:
    """
    Stores audio in file store, creates template record in 'pending' state,
    notifies workspace admins via inbox (Prompt 24).
    """
    audio_file_id = await file_store.save(
        workspace_id=workspace_id,
        path=f"voice-templates/{category_id}/{language_code}/{uuid4()}.wav",
        content=audio_bytes,
        content_type="audio/wav",
    )
    # validate: audio must be 16kHz 16-bit mono WAV, 1-30 seconds
    validate_audio_format(audio_bytes)

    template = await db.insert("voice_templates", {
        "category_id": category_id,
        "language_code": language_code,
        "audio_file_id": audio_file_id,
        "transcript": transcript,
        "transcript_english": transcript_english,
        "duration_seconds": get_audio_duration(audio_bytes),
        "recorded_by": recorded_by,
        "recorded_at": recorded_at,
        "dialect_note": dialect_note,
        "status": "pending",
        "workspace_id": workspace_id,
    })
    await inbox.notify(workspace_id, f"New voice template submitted for '{language_code}' - {category_id}. Review in Settings > Voice Templates.")
    return template

async def approve_template(template_id: UUID, approver_user_id: UUID, quality_rating: int) -> None:
    """Approves the template. Replaces any existing approved template for this category+language."""
    await db.execute(
        """UPDATE voice_templates
           SET status = 'approved', approved_by_user_id = $2, approved_at = NOW(),
               quality_rating = $3
           WHERE id = $1""",
        template_id, approver_user_id, quality_rating,
    )
    # Archive any previously approved template for the same slot
    await db.execute(
        """UPDATE voice_templates
           SET status = 'archived'
           WHERE category_id = (SELECT category_id FROM voice_templates WHERE id = $1)
           AND language_code = (SELECT language_code FROM voice_templates WHERE id = $1)
           AND workspace_id = (SELECT workspace_id FROM voice_templates WHERE id = $1)
           AND id != $1 AND status = 'approved'""",
        template_id,
    )
```

---

## API Endpoints

```
GET    /api/voice-templates/categories
       Returns: all registered categories with labels and domain

GET    /api/voice-templates/coverage
       Returns: per-language coverage report (how many categories have approved templates)

GET    /api/voice-templates
       Query: language_code, category_id, status
       Returns: paginated list of templates

POST   /api/voice-templates
       Multipart form: audio_file, category_id, language_code, transcript,
                       transcript_english, recorded_by, recorded_at, dialect_note?
       Returns: { template_id, status: 'pending' }

GET    /api/voice-templates/{id}
       Returns: template metadata + audio stream URL

GET    /api/voice-templates/{id}/audio
       Returns: audio file download (WAV)

POST   /api/voice-templates/{id}/approve
       Body: { quality_rating: 1-5 }
       Admin only. Sets status to 'approved'.

POST   /api/voice-templates/{id}/reject
       Body: { reason }
       Admin only.

DELETE /api/voice-templates/{id}
       Archives the template (does not delete the audio file from file store).

POST   /api/voice-templates/assemble
       Body: { category_id, language_code, dynamic_text?, full_text_fallback, workspace_id }
       Returns: { audio_url?, transcript, method }
       Used by the runtime to assemble voice responses.

POST   /api/voice-templates/categories/register
       Admin only. Registers a custom category (used by domain packs at load time).
       Body: IntentTemplateCategorySchema
```

---

## Management UI

`/settings/voice-templates`

**Coverage dashboard:** Grid of languages vs categories. Green cell = approved template exists. Yellow = pending. Empty = no template.

**Upload form:** select category, select language (from workspace's configured languages), upload WAV file, enter transcript in native language and English translation, enter recorded-by name, optional dialect note.

**Pending review queue:** list of pending templates with audio player. Star rating selector (1-5). Approve/Reject buttons. Rejection reason text field shown on reject.

**Language fallback configuration:** for each supported language, set the fallback language to use when a template is missing. Default: Twi falls back to English. Fante falls back to Twi.

---

## Acceptance Criteria

- `get_template("greeting", "ak-GH", workspace_id)` returns the approved Twi greeting template.
- `get_template("greeting", "fan-GH", workspace_id)` returns the Twi fallback when no Fante template exists and Twi is configured as Fante's fallback.
- `get_template("greeting", "de-DE", workspace_id)` returns `None` (German not in the system).
- `assemble_response("greeting", "ak-GH", None, "Hello", workspace_id)` returns `method = "template"` and `audio_url` pointing to the Twi greeting audio.
- `assemble_response("quote_ready", "ak-GH", "GHS 4,500", "Your quote is ready: GHS 4,500", workspace_id)` returns `method = "template_tts_hybrid"` with combined audio.
- `assemble_response("greeting", "dag-GH", None, "Hello", workspace_id)` when no Dagbani template exists and no TTS support returns `method = "text_only"`.
- Uploading a non-WAV file returns HTTP 422.
- Uploading a WAV longer than 30 seconds returns HTTP 422.
- Approving a template when another approved template already exists for the same slot archives the previous one.
- `GET /api/voice-templates/coverage` returns a per-language breakdown with correct counts.
- Play count increments on every template serve.
- Template audio is served via `audio_file_id` through the file store and requires workspace authentication.
