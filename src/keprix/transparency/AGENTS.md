# AI transparency and SGI compliance rules

1. Every AI generation endpoint MUST call `prepare_ai_call` before sending user
   input to a model, and MUST call `finalize_ai_output` (or
   `GenerationLogStore.log_generation` + `SgiLabeler.label_output`) before
   returning output to a user.
2. Every AI output MUST carry a visible SGI disclosure. No exceptions for
   "internal" or "draft" surfaces that end users can see.
3. The generation log is append-only. Never UPDATE or DELETE rows. Application
   helpers raise `ImmutableLogError` if mutation is attempted.
4. Consent must be obtained (affirmative, granular, per feature) before ANY
   user input enters an AI model. Withdrawal is a new append-only entry.
5. Disclosure text must be available in English, French, German, and Spanish
   for EU-facing deployments.
6. Labels are non-removable in the UI (no dismiss/hide control for end users).
