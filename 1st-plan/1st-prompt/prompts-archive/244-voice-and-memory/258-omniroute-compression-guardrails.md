# Keprix - Prompt 80: Adopt OmniRoute; Compression, Resilience & Guardrails

## Context

OmniRoute's token compression (RTK + Caveman) saves 15-95% of tokens per request. Its resilience layer provides model lockout settings and graceful degradation. Its guardrails include PII masking, prompt injection defence, and vision bridge routing.

These are capabilities Keprix doesn't currently have. Adopting them makes every agent interaction cheaper, safer, and more reliable.

## Reference Clone

`planning/competitor-research/agents-to-adopt/omniroute/`

Key source files:
```
src/lib/compression/; judgeModelClient.ts (RTK + Caveman compression)
src/lib/resilience/; modelLockoutSettings, circuit breaker patterns
src/lib/guardrails/; piiMasker.ts, promptInjection.ts, visionBridge.ts
src/lib/compliance/; noLog.ts, providerAudit.ts
```

## What to Adopt

### Layer 1: Token Compression

OmniRoute's compression is stacked; RTK compresses the request, Caveman compresses the response. Combined savings: 15-95%, averaging ~89% on tool-heavy agent sessions.

```
REQUEST FLOW WITH COMPRESSION:

  Agent message
       │
  ┌────▼──────────────────────────────┐
  │  RTK COMPRESSION                  │
  │  ──────────────────────────────── │
  │  - Remove redundant context       │
  │  - Summarise long tool outputs    │
  │  - Deduplicate repeated content   │
  │  - Compress conversation history  │
  │                                   │
  │  Savings: 15-60%                  │
  └────┬──────────────────────────────┘
       │  Compressed prompt
       ▼
  ┌──────────────────────────────────┐
  │  LLM Provider                     │
  └────┬──────────────────────────────┘
       │  Raw response
       ▼
  ┌────▼──────────────────────────────┐
  │  CAVEMAN DECOMPRESSION           │
  │  ──────────────────────────────── │
  │  - Expand abbreviated output      │
  │  - Restore full code blocks       │
  │  - Rehydrate tool calls           │
  │                                   │
  │  Savings: 20-80% on response      │
  └────┬──────────────────────────────┘
       │  Full response
       ▼
  Agent receives complete output
```

### Layer 2: Resilience

```
RESILIENCE PATTERNS:

1. MODEL LOCKOUT
   - Per-provider lockout after N consecutive failures
   - Exponential backoff: 5s → 10s → 20s → 40s → 80s
   - Auto-recovery probe after lockout expires

2. GRACEFUL DEGRADATION
   - If no provider in tier is healthy → degrade to next tier
   - If all tiers exhausted → fallback to local model
   - Never return 503; always have a fallback path

3. REQUEST BUFFERING
   - Buffer requests during provider switch (no dropped messages)
   - Retry with exponential backoff on transient errors
   - Timeout escalation: 30s → 60s → 120s per tier

4. HEALTH PROBING
   - Passive: track success/failure per request
   - Active: periodic health check ping to each provider
   - Circuit breaker: N failures in window → open circuit
```

### Layer 3: Guardrails

```
GUARDRAIL PIPELINE:

  Outgoing request
       │
  ┌────▼──────────────┐
  │  PII MASKER       │  ← Adopt from piiMasker.ts
  │  ──────────────── │
  │  - Detect emails   │
  │  - Detect phone #s │
  │  - Detect API keys │
  │  - Detect IPs      │
  │  - Replace: [EMAIL]│
  └────┬──────────────┘
       │
  ┌────▼──────────────┐
  │  PROMPT INJECTION │  ← Adopt from promptInjection.ts
  │  ──────────────── │
  │  - Detect "ignore" │
  │  - Detect "system" │
  │  - Detect roleplay │
  │  - Block or flag   │
  └────┬──────────────┘
       │
  ┌────▼──────────────┐
  │  VISION BRIDGE    │  ← Adopt from visionBridge.ts
  │  ──────────────── │
  │  - Route images to │
  │    vision-capable  │
  │    provider        │
  │  - Fallback: text  │
  │    description     │
  └───────────────────┘
```

## Files To Create

```text
src/keprix/providers/compression/
  __init__.py
  rtk.py                 # RTK request compression (adopt from judgeModelClient.ts)
  caveman.py             # Caveman response decompression
  compressor.py          # Unified compression pipeline
  context_dedup.py       # Conversation history deduplication
  tool_output_summary.py # Summarise long tool outputs before sending to LLM
  token_counter.py       # Pre and post compression token counting
  
src/keprix/providers/resilience/
  __init__.py
  model_lockout.py       # Per-provider lockout with exponential backoff
  graceful_degrade.py    # Graceful tier degradation
  health_prober.py       # Active health checking
  request_buffer.py      # Buffer during provider transitions
  timeout_escalator.py   # Timeout escalation per tier

src/keprix/providers/guardrails/
  __init__.py
  pii_masker.py          # PII detection and masking (adopt from piiMasker.ts)
  prompt_injection.py    # Prompt injection defence (adopt from promptInjection.ts)
  vision_bridge.py       # Image routing to vision-capable providers
  pipeline.py            # Guardrail pipeline orchestration

src/keprix/providers/compliance/
  __init__.py
  no_log.py              # No-log mode for sensitive requests (adopt from noLog.ts)
  provider_audit.py      # Provider audit trail (adopt from providerAudit.ts)
  data_residency.py      # Optional: route to providers in specific regions

tests/providers/compression/
  test_rtk.py
  test_caveman.py
  test_compressor.py
  test_context_dedup.py

tests/providers/resilience/
  test_model_lockout.py
  test_graceful_degrade.py
  test_health_prober.py

tests/providers/guardrails/
  test_pii_masker.py
  test_prompt_injection.py
  test_vision_bridge.py
```

## Implementation Details

### RTK Compression (adopt from `judgeModelClient.ts`)

```python
class RTKCompressor:
    """Request Token Kompression; reduces token count before sending to LLM."""
    
    STRATEGIES = ["aggressive", "balanced", "minimal", "none"]
    
    async def compress(
        self,
        messages: list[Message],
        strategy: str = "balanced",
        max_tokens: int | None = None,
    ) -> CompressedRequest:
        """Compress the outgoing message list."""
        
        result = messages
        
        if strategy == "none":
            return CompressedRequest(result, savings=0)
        
        # 1. Conversation history deduplication
        if len(result) > 10:
            result = self._deduplicate_history(result)
        
        # 2. Summarise long tool outputs
        if strategy in ("aggressive", "balanced"):
            result = await self._summarise_tool_outputs(result)
        
        # 3. Context window trimming
        if max_tokens:
            result = self._trim_to_token_budget(result, max_tokens)
        
        # 4. Remove redundant system messages
        result = self._merge_system_messages(result)
        
        original_tokens = count_tokens(messages)
        compressed_tokens = count_tokens(result)
        savings = 1 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0
        
        return CompressedRequest(result, savings=savings, original_tokens=original_tokens, compressed_tokens=compressed_tokens)
    
    def _deduplicate_history(self, messages: list[Message]) -> list[Message]:
        """Remove repeated message pairs (common in agent loops)."""
        seen = set()
        deduped = []
        for msg in messages:
            key = (msg.role, hash(msg.content[:200]))
            if key not in seen:
                seen.add(key)
                deduped.append(msg)
        return deduped
    
    async def _summarise_tool_outputs(self, messages: list[Message]) -> list[Message]:
        """Summarise long tool outputs (>1000 tokens) into concise summaries."""
        result = []
        for msg in messages:
            if msg.role == "tool" and count_tokens(msg.content) > 1000:
                summary = await self._summarise_with_cheap_model(msg.content)
                msg.content = f"[Tool output summary: {summary}]"
            result.append(msg)
        return result
```

### Caveman Decompressor

```python
class CavemanDecompressor:
    """Expands compressed LLM responses back to full form."""
    
    async def decompress(self, response: ChatResponse, original_context: list[Message]) -> ChatResponse:
        """Rehydrate abbreviated responses using original context."""
        
        # If the response was generated with compression, it may have:
        # - Abbreviated function names → expand to full
        # - Shortened code blocks → restore from context
        # - Omitted repeated content → fill from conversation history
        
        content = response.content
        
        # Restore tool calls from abbreviated names
        if response.tool_calls:
            for tc in response.tool_calls:
                tc.function.name = self._expand_tool_name(tc.function.name, original_context)
        
        # Restore code blocks
        if "```" in content and len(content) < 500:
            content = self._rehydrate_code_blocks(content, original_context)
        
        response.content = content
        return response
```

### PII Masker (adopt from `piiMasker.ts`)

```python
class PIIMasker:
    """Detects and masks personally identifiable information in outgoing requests."""
    
    PATTERNS = {
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "PHONE_UK": r'\b(?:\+44|0)7\d{9}\b',
        "PHONE_US": r'\b\+?1?\d{10}\b',
        "IPV4": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        "IPV6": r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
        "CREDIT_CARD": r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b',
        "SSN": r'\b\d{3}-\d{2}-\d{4}\b',
        "API_KEY": r'\b(sk-[a-zA-Z0-9]{20,}|[a-zA-Z0-9]{32,})\b',
    }
    
    REPLACEMENTS = {
        "EMAIL": "[EMAIL]",
        "PHONE_UK": "[PHONE]",
        "PHONE_US": "[PHONE]",
        "IPV4": "[IP]",
        "IPV6": "[IP]",
        "CREDIT_CARD": "[CARD]",
        "SSN": "[SSN]",
        "API_KEY": "[API_KEY]",
    }
    
    def mask(self, text: str) -> tuple[str, list[MaskRecord]]:
        records = []
        for label, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                records.append(MaskRecord(
                    type=label,
                    original=match.group(),
                    position=match.start(),
                ))
                text = text[:match.start()] + self.REPLACEMENTS[label] + text[match.end():]
        return text, records
    
    def unmask(self, text: str, records: list[MaskRecord]) -> str:
        for record in sorted(records, key=lambda r: r.position, reverse=True):
            text = text[:record.position] + record.original + text[record.position + len(self.REPLACEMENTS[record.type]):]
        return text
```

### Prompt Injection Defence

```python
class PromptInjectionDefence:
    """Detects and blocks prompt injection attempts."""
    
    INJECTION_PATTERNS = [
        r'(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions?',
        r'(?i)you\s+are\s+now\s+(a\s+)?(different|new)\s+(role|persona|system)',
        r'(?i)system\s*:\s*you\s+are',
        r'(?i)forget\s+(everything|all)\s+(you\s+know|before)',
        r'(?i)act\s+as\s+(if\s+you\s+are|a\s+different)',
        r'(?i)your\s+(new\s+)?system\s+(prompt|instruction)s?\s+(is|are)',
    ]
    
    def detect(self, text: str) -> InjectionResult:
        for pattern in self.INJECTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return InjectionResult(
                    detected=True,
                    pattern=pattern,
                    match=match.group(),
                    position=match.start(),
                    severity="HIGH" if "system" in match.group().lower() else "MEDIUM",
                )
        return InjectionResult(detected=False)
    
    def block(self, text: str) -> bool:
        result = self.detect(text)
        if result.detected and result.severity == "HIGH":
            return True  # Block
        if result.detected and result.severity == "MEDIUM":
            # Log and allow; could be legitimate
            logger.warning(f"Potential prompt injection: {result.match}")
            return False
        return False
```

## Safety; Non-Breaking

1. **Compression is opt-in per combo.** Existing combos use `compression: none`. New combos can opt in.
2. **Guardrails are configurable.** Can be disabled entirely, or set to `warn` (log only) vs `block`.
3. **PII masking is reversible.** Records allow unmasking in the response so the agent sees correct data.
4. **Resilience extends existing error handling.** Current errors still propagate; resilience adds recovery.
5. **No performance regression.** Compression is async and non-blocking. Cache frequently compressed contexts.

## Verification

- [ ] RTK compression saves 15-60% tokens on typical agent conversations
- [ ] Caveman decompression restores abbreviated output correctly
- [ ] PII masker correctly detects and masks emails, phones, IPs, API keys
- [ ] PII unmask restores original values in tool output
- [ ] Prompt injection defence detects "ignore previous instructions" pattern
- [ ] Prompt injection defence allows legitimate system-like messages through
- [ ] Model lockout engages after 5 consecutive failures
- [ ] Circuit breaker auto-recovers after cooldown
- [ ] Graceful degradation falls through all tiers to local model
- [ ] Health prober detects provider recovery and reinstates
- [ ] No-log mode prevents request content from being logged
- [ ] Provider audit trail records all routing decisions
- [ ] All existing tests pass with compression disabled (default)
- [ ] Tests pass for all new modules
