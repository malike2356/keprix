# keprix - Prompt 50: Localization Data Flywheel and Correction Loop

## Context

Read `35-localization-language-voice.md`, `93-african-language-provider-adapters.md`, and `94-structured-intent-extraction-engine.md` first. Also read `keprix-projects/abbis/LOCALIZATION-COMBINED-STRATEGY.md`.

Prompt 27 added a `human_review_required` flag to localization audit records. This prompt builds what happens next: a full correction workflow where operator-confirmed corrections feed back into the system immediately and accumulate into a proprietary fine-tuning dataset over time.

The central insight is that every correction is an investment. A corrected Twi borehole term applied immediately helps the current user. That same correction, staged as a training pair, improves model accuracy for every future user who speaks Twi in a borehole context. After 12 months of production use, AbbiS will hold thousands of domain-specific African language corrections that no competitor has. This is a moat that compounds with usage.

This prompt builds the collection infrastructure. Fine-tuning execution is a data-science task run periodically when sufficient data accumulates; it is not automated in v1. The staging format specified here (SM4T JSON Lines) means the data is ready whenever the fine-tuning run happens.

---

## File Structure

```
keprix/backend/localization/
    corrections.py          - correction queue, submission, approval
    flywheel.py             - export, quality metrics, staging pipeline
    routes_corrections.py   - API endpoints

keprix/tests/localization/
    test_corrections.py
    test_flywheel.py

keprix/ui/web/src/app/(workspace)/settings/localization/
    corrections/page.tsx    - operator correction review UI
    metrics/page.tsx        - quality metrics dashboard
```

---

## Database Schema

```sql
CREATE TABLE localization_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_record_id UUID NOT NULL REFERENCES localization_audit(id),
    -- the audit record this correction refers to
    workspace_id UUID NOT NULL,
    correction_type TEXT NOT NULL,
    -- see correction types below
    original_value TEXT NOT NULL,
    -- what the system produced (transcription, translation, detected intent, etc.)
    corrected_value TEXT NOT NULL,
    -- what the operator (or user) says it should be
    source_language TEXT NOT NULL,
    -- BCP 47 code of the original language
    target_language TEXT,
    -- for translation corrections: the target language
    domain TEXT NOT NULL DEFAULT 'generic',
    -- which domain pack this correction belongs to
    submitted_by_user_id UUID,
    -- null if submitted by the end user directly (user correction flow)
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'approved', 'rejected'
    reviewed_by_user_id UUID,
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    applied_to_glossary BOOLEAN NOT NULL DEFAULT FALSE,
    staged_for_training BOOLEAN NOT NULL DEFAULT FALSE,
    -- set true when exported to localization_training_samples
    training_sample_id UUID
    -- FK to localization_training_samples once staged
);

CREATE INDEX ON localization_corrections(workspace_id, status, correction_type);
CREATE INDEX ON localization_corrections(source_language, domain, status);
CREATE INDEX ON localization_corrections(staged_for_training);

CREATE TABLE localization_training_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correction_id UUID NOT NULL REFERENCES localization_corrections(id),
    task_type TEXT NOT NULL,
    -- 's2t', 't2t', 't2s' - matches SM4T task type codes
    source_language TEXT NOT NULL,
    target_language TEXT,
    source_text TEXT,
    -- for s2t: the transcript that was wrong (text form of what should have been recognized)
    source_audio_file_id UUID,
    -- for s2t: the audio file from the audit record (if available)
    target_text TEXT NOT NULL,
    -- the corrected output (what the model should have produced)
    domain TEXT NOT NULL DEFAULT 'generic',
    quality_score SMALLINT NOT NULL DEFAULT 3,
    -- 1-5; operator-assigned during review; used to weight training data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    included_in_export_at TIMESTAMPTZ
    -- set when this sample is written to a fine-tuning export file
);

CREATE INDEX ON localization_training_samples(task_type, source_language, included_in_export_at);
```

---

## Correction Types

Six named types, each with its own meaning and training impact:

| Correction Type | What It Fixes | Training Impact |
|---|---|---|
| `transcription` | Speech-to-text got the words wrong | S2T training pair (audio, corrected transcript) |
| `translation` | Translation from local language to English was wrong | T2T training pair (source text, corrected English) |
| `intent` | Extracted intent was wrong | LLM fine-tuning data (not SM4T; intent uses the LLM) |
| `entity` | An entity value was wrong (e.g. depth extracted as 30m when user said 300m) | LLM fine-tuning data |
| `response_translation` | The response translated back to the user's language was wrong | T2T training pair (English source, corrected local-language target) |
| `glossary_addition` | A term needs adding to the domain glossary (not a correction per se, but surfaces here) | Glossary update, also influences future translations |

`intent` and `entity` corrections are LLM prompting improvements, not SM4T training. They are exported in a different format (see Flywheel section below). SM4T only receives `transcription`, `translation`, and `response_translation` corrections.

---

## Corrections Workflow

```python
# keprix/backend/localization/corrections.py

class LocalizationCorrectionQueue:

    async def submit_user_correction(
        self,
        audit_record_id: UUID,
        correction_type: str,
        original_value: str,
        corrected_value: str,
        workspace_id: str,
    ) -> CorrectionRecord:
        """
        End-user submits a correction (e.g. via thumbs-down on a translation).
        Goes to 'pending' queue for operator review.
        Sends inbox notification to workspace admin.
        """
        record = await self._insert_correction(
            audit_record_id=audit_record_id,
            correction_type=correction_type,
            original_value=original_value,
            corrected_value=corrected_value,
            workspace_id=workspace_id,
            submitted_by_user_id=None,
        )
        await inbox.notify(workspace_id,
            f"User submitted a localization correction ({correction_type}). Review in Settings > Localization > Corrections.")
        return record

    async def submit_operator_correction(
        self,
        audit_record_id: UUID,
        correction_type: str,
        original_value: str,
        corrected_value: str,
        workspace_id: str,
        operator_user_id: UUID,
        auto_approve: bool = True,
    ) -> CorrectionRecord:
        """
        Operator submits a correction directly from the review UI.
        If auto_approve is True (default for operators), skips the pending queue
        and goes straight to 'approved', triggers immediate effects.
        """
        record = await self._insert_correction(
            audit_record_id=audit_record_id,
            correction_type=correction_type,
            original_value=original_value,
            corrected_value=corrected_value,
            workspace_id=workspace_id,
            submitted_by_user_id=operator_user_id,
        )
        if auto_approve:
            await self.approve_correction(record.id, operator_user_id)
        return record

    async def approve_correction(
        self,
        correction_id: UUID,
        reviewer_user_id: UUID,
        quality_score: int = 3,
    ) -> None:
        """
        Approves a pending correction. Triggers:
        1. Immediate application (glossary, if glossary_addition).
        2. Staging as a training sample.
        """
        await db.execute(
            """UPDATE localization_corrections
               SET status = 'approved', reviewed_by_user_id = $2, reviewed_at = NOW()
               WHERE id = $1""",
            correction_id, reviewer_user_id,
        )
        correction = await self._get(correction_id)
        await self._apply_immediate_effects(correction)
        await self._stage_for_training(correction, quality_score)

    async def _apply_immediate_effects(self, correction: CorrectionRecord) -> None:
        """
        For 'glossary_addition': upserts the term into the domain glossary.
        For 'translation' and 'response_translation': adds as an override entry
        in the workspace translation cache so future identical phrases use the
        corrected translation directly (bypassing the model for known phrases).
        """
        if correction.correction_type == "glossary_addition":
            await glossary_service.upsert_term(
                domain=correction.domain,
                source_language=correction.source_language,
                source_term=correction.original_value,
                translated_term=correction.corrected_value,
                workspace_id=correction.workspace_id,
                source="operator_correction",
            )
            await db.execute(
                "UPDATE localization_corrections SET applied_to_glossary = TRUE WHERE id = $1",
                correction.id,
            )
        elif correction.correction_type in ("translation", "response_translation"):
            await translation_cache.set_override(
                workspace_id=correction.workspace_id,
                source_language=correction.source_language,
                target_language=correction.target_language,
                source_text=correction.original_value,
                corrected_text=correction.corrected_value,
            )

    async def _stage_for_training(
        self,
        correction: CorrectionRecord,
        quality_score: int,
    ) -> None:
        """Writes a training sample record for SM4T-compatible corrections."""
        if correction.correction_type not in ("transcription", "translation", "response_translation"):
            # Intent and entity corrections are LLM data, not SM4T data.
            # Mark staged anyway so the export picks them up separately.
            pass

        task_type_map = {
            "transcription": "s2t",
            "translation": "t2t",
            "response_translation": "t2t",
        }
        task_type = task_type_map.get(correction.correction_type)
        if not task_type:
            return

        audit_record = await localization_audit.get(correction.audit_record_id)
        sample_id = await db.insert("localization_training_samples", {
            "correction_id": correction.id,
            "task_type": task_type,
            "source_language": correction.source_language,
            "target_language": correction.target_language,
            "source_text": correction.original_value if task_type == "t2t" else None,
            "source_audio_file_id": audit_record.audio_file_id if task_type == "s2t" else None,
            "target_text": correction.corrected_value,
            "domain": correction.domain,
            "quality_score": quality_score,
        })
        await db.execute(
            "UPDATE localization_corrections SET staged_for_training = TRUE, training_sample_id = $2 WHERE id = $1",
            correction.id, sample_id,
        )
```

---

## Translation Cache Override

When an operator confirms that a specific phrase translates to a specific target, future occurrences of that exact phrase bypass the model entirely:

```python
# keprix/backend/localization/translation_cache.py (addition)

class TranslationCacheOverride:
    """
    Workspace-level overrides for known translation errors.
    Checked before calling any provider.
    """

    async def get_override(
        self,
        workspace_id: str,
        source_language: str,
        target_language: str,
        source_text: str,
    ) -> str | None:
        """Returns the override if one exists, else None."""
        row = await db.fetchone(
            """SELECT corrected_text FROM translation_overrides
               WHERE workspace_id = $1 AND source_language = $2
               AND target_language = $3 AND source_text = $4""",
            workspace_id, source_language, target_language, source_text,
        )
        return row["corrected_text"] if row else None

    async def set_override(self, workspace_id, source_language, target_language, source_text, corrected_text):
        await db.execute(
            """INSERT INTO translation_overrides
               (workspace_id, source_language, target_language, source_text, corrected_text)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (workspace_id, source_language, target_language, source_text)
               DO UPDATE SET corrected_text = EXCLUDED.corrected_text, updated_at = NOW()""",
            workspace_id, source_language, target_language, source_text, corrected_text,
        )
```

The translation pipeline checks the override cache before calling any provider:

```python
# In language_middleware.py translate() function, add before provider call:
override = await translation_cache_override.get_override(
    workspace_id, source_language, target_language, text
)
if override:
    return TranslationResult(text=override, provider="override_cache", confidence=1.0)
```

---

## Flywheel Export

The flywheel export converts staged training samples into the format SeamlessM4T expects for fine-tuning. This runs on demand (a CLI command or a scheduled job) when the operator decides there is enough data.

```python
# keprix/backend/localization/flywheel.py

class LocalizationFlywheel:

    async def export_sm4t_training_data(
        self,
        output_dir: Path,
        domain: str | None = None,
        task_type: str | None = None,
        min_quality_score: int = 3,
        since: datetime | None = None,
    ) -> ExportSummary:
        """
        Exports approved, un-exported training samples to JSONL format
        compatible with SeamlessM4T fine-tuning.

        Output structure:
        output_dir/
          t2t_ak-GH_en.jsonl      - Twi-to-English translation pairs
          t2t_en_ak-GH.jsonl      - English-to-Twi translation pairs
          s2t_ak-GH.jsonl         - Twi speech-to-text pairs (manifest format)
          [one file per task+language combination]
          manifest.json           - export summary and counts
        """
        samples = await self._get_unstaged_samples(domain, task_type, min_quality_score, since)
        grouped = self._group_by_task_and_language(samples)
        written = {}

        for (task, src_lang, tgt_lang), group in grouped.items():
            filename = self._make_filename(task, src_lang, tgt_lang)
            path = output_dir / filename
            lines_written = await self._write_jsonl(path, task, group)
            written[filename] = lines_written

        # Mark samples as exported
        sample_ids = [s.id for s in samples]
        await db.execute(
            "UPDATE localization_training_samples SET included_in_export_at = NOW() WHERE id = ANY($1)",
            sample_ids,
        )

        manifest = {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "total_samples": len(samples),
            "files": written,
            "domains": list({s.domain for s in samples}),
        }
        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        return ExportSummary(**manifest)

    async def _write_jsonl(self, path: Path, task: str, samples: list) -> int:
        """Writes samples in SM4T fine-tuning format."""
        count = 0
        with path.open("w") as f:
            for sample in samples:
                if task == "t2t":
                    record = {
                        "src_lang": sample.source_language,
                        "tgt_lang": sample.target_language,
                        "src_text": sample.source_text,
                        "tgt_text": sample.target_text,
                        "quality_score": sample.quality_score,
                        "domain": sample.domain,
                    }
                elif task == "s2t":
                    record = {
                        "src_lang": sample.source_language,
                        "audio_path": str(await file_store.get_local_path(sample.source_audio_file_id)),
                        "transcript": sample.target_text,
                        "quality_score": sample.quality_score,
                        "domain": sample.domain,
                    }
                f.write(json.dumps(record) + "\n")
                count += 1
        return count

    async def export_llm_correction_data(
        self,
        output_dir: Path,
        domain: str | None = None,
        since: datetime | None = None,
    ) -> dict:
        """
        Exports intent and entity corrections in a format suitable for LLM instruction
        fine-tuning (system/user/assistant format). These do not go to SM4T.

        Each record: {"system": "...", "user": "...", "assistant": "..."}
        where user is the translated input and assistant is the correct structured JSON.
        """
        # Fetch intent and entity correction records linked to their audit records
        corrections = await db.fetchall(
            """SELECT c.*, la.translated_input, la.extracted_intent_json
               FROM localization_corrections c
               JOIN localization_audit la ON la.id = c.audit_record_id
               WHERE c.correction_type IN ('intent', 'entity')
               AND c.status = 'approved'
               AND c.staged_for_training = FALSE""",
        )
        path = output_dir / "intent_entity_corrections.jsonl"
        count = 0
        with path.open("w") as f:
            for row in corrections:
                record = {
                    "system": "Extract intent and entities from this borehole industry message. Return JSON.",
                    "user": row["translated_input"],
                    "assistant": row["corrected_value"],
                    "domain": row["domain"],
                    "correction_type": row["correction_type"],
                }
                f.write(json.dumps(record) + "\n")
                count += 1
        return {"intent_entity_corrections": count}
```

---

## Quality Metrics

```python
# keprix/backend/localization/flywheel.py (continued)

class LocalizationQualityMetrics:

    async def get_correction_rate(
        self,
        workspace_id: str,
        language_code: str | None = None,
        since: datetime | None = None,
    ) -> dict:
        """
        Returns correction rate: corrections / total audit records.
        Breakdown by correction_type.
        """

    async def get_provider_accuracy_by_language(self) -> dict:
        """
        For each provider + language combination, computes:
        - Total responses
        - Total corrections
        - Correction rate (proxy for accuracy)
        Grouped by month.
        """

    async def get_most_corrected_terms(
        self,
        domain: str,
        language_code: str,
        limit: int = 20,
    ) -> list[dict]:
        """
        Returns the 20 most frequently corrected source terms for this domain/language.
        These candidates should be reviewed for addition to the domain glossary.
        """

    async def get_coverage_summary(self, workspace_id: str) -> dict:
        """
        Returns per-language:
        - Interaction count (from audit records)
        - Correction count (total and by type)
        - Training samples staged
        - Training samples exported
        - Estimated next fine-tune readiness (threshold: 500 samples per language per task)
        """
```

---

## API Endpoints

```
GET    /api/localization/corrections
       Query: status, correction_type, source_language, domain
       Returns: paginated list with audit record context

POST   /api/localization/corrections
       Body: { audit_record_id, correction_type, original_value, corrected_value }
       End-user correction submission.

GET    /api/localization/corrections/{id}
       Returns: full correction record with linked audit record

POST   /api/localization/corrections/{id}/approve
       Body: { quality_score: 1-5 }
       Operator only. Approves and triggers immediate effects.

POST   /api/localization/corrections/{id}/reject
       Body: { reason }
       Operator only.

GET    /api/localization/metrics
       Returns: correction rates, provider accuracy, coverage summary
       Query: workspace_id, language_code, since

GET    /api/localization/metrics/top-errors
       Query: domain, language_code, limit
       Returns: most corrected terms and their correction rates

POST   /api/localization/flywheel/export
       Admin only. Triggers training data export.
       Body: { output_path, domain?, task_type?, min_quality_score?, since? }
       Returns: export manifest summary
```

---

## Operator Review UI

`/settings/localization/corrections`

**Corrections queue:** List of pending corrections with filters for language, correction type, domain. Each row shows: original value (what system produced), corrected value (what was submitted), correction type, source language, submitted at, submitted by (user or operator name). Clicking opens the full correction detail.

**Correction detail:** Shows the full audit record context - the original voice or text input, the transcription, the translation, the extracted intent, and the response. Highlights where in the pipeline the error occurred. Allows operator to edit the corrected value before approving (in case the user's correction is itself inaccurate). Quality score selector (1-5 stars). Approve and Reject buttons.

**Batch approval:** Select multiple corrections of the same type and approve them all with the same quality score.

**Glossary integration:** Approving a `glossary_addition` correction shows a preview of the glossary entry that will be created, and allows the operator to edit the definition before confirming.

---

## Metrics Dashboard

`/settings/localization/metrics`

**Correction rate over time:** Line chart per language, last 90 days. Dropping correction rate signals improving model quality.

**Provider accuracy table:** Grid of provider vs language vs task. Shows correction rate as a proxy for accuracy. Highlights cells where rate is >10% (worth investigating).

**Training readiness:** Per language and task type, shows count of staged samples vs the 500-sample threshold. Progress bar. Button to trigger export when threshold is met.

**Most-corrected terms:** Table of the top 20 terms being corrected per language. These are candidates for glossary entries. "Add to glossary" action on each row.

---

## Acceptance Criteria

- Submitting a user correction creates a record in `pending` state and sends an inbox notification.
- Operator auto-approve creates a record and immediately applies effects (glossary upsert for `glossary_addition`, translation cache override for translation corrections).
- After approving a `translation` correction, the next translation request with the same source text returns the override value, not the model output.
- After approving a `glossary_addition` correction, the term appears in the domain glossary and is applied by the glossary service on the next request.
- Training sample is created with correct `task_type` on correction approval.
- `export_sm4t_training_data` produces JSONL files with valid records and a manifest.
- Exported samples are marked with `included_in_export_at` and are not included in subsequent exports.
- `get_provider_accuracy_by_language` returns a populated result after at least one correction is approved.
- The correction review UI shows the full audit pipeline context for each correction.
- Rejecting a correction with no reason returns HTTP 422.
- `intent` and `entity` corrections are exported to the LLM export file, not the SM4T export file.
