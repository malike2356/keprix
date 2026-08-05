# Prompt {prompt_number}; Adopt Hermes Feature: {feature_name}

## Upstream Source
- **Hermes version:** {version}
- **Release date:** {release_date}
- **Release URL:** {release_url}
- **Category:** {category}

## What Hermes Added
{description}

## Upstream Enrichment
{enrichment}

## Security Assessment
{security_assessment}

## What Keprix Builds

### 1. Feature Implementation
{implementation_notes}

### 2. Security Hardening
{hardening_notes}

### 3. Scout Integration
- Signal types to emit: governance/upstream events for adoption lifecycle
- Governance rules to add: tool blocks, egress allowlist updates, or rate limits as needed
- ScoutListener commands: only if the feature exposes operator-controllable runtime behavior

### 4. Tests
- Functional tests for the adopted capability
- Security tests: injection, sandbox escape, credential leak
- Scout integration tests for emitted signals

## Files to Create/Modify
- `src/keprix/`; core implementation for the adopted feature
- `tests/`; functional and security coverage

## Acceptance Criteria
- [ ] Feature works as described
- [ ] Passes all security tests
- [ ] Scout signals emitted correctly
- [ ] Governance rules triggered appropriately
- [ ] No regression in existing tests
- [ ] Parity gates pass: `check-tui-parity.sh`, `check-tui-surpass-hermes.sh`, `check-agent-parity.sh`
- [ ] Inventory closed: `keprix upstream complete <feature_id> --equivalent <capability-id>`
