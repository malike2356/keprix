# keprix - Prompt 99: Agent Persona; SAGE, Research & Intelligence

## Context

SAGE is the research persona. It handles web research, knowledge synthesis, market intelligence, competitive analysis, and briefing generation. Built on keprix's deep research pipeline (Prompt 14) and RAG knowledge base (Prompt 06).

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Prerequisites

- Prompt 96 (Persona base and registry); must exist
- Prompt 14 (Deep research and playbook); must be complete
- Prompt 06 (Memory and RAG); must be complete

## Files To Create

```text
backend/personas/sage/
  __init__.py
  persona.py           # SAGE personality definition
  researcher.py        # Research pipeline and source management
  briefer.py           # Briefing and report generation
  intel.py             # Market intelligence and trend analysis
  prompts/
    system.md          # System prompt for SAGE
    research_brief.md  # Research brief template
    source_eval.md     # Source credibility rubric
tests/personas/
  test_sage_researcher.py
  test_sage_briefer.py
  test_sage_intel.py
```

## Persona Definition

### Identity
- **Name:** SAGE
- **Role:** Research & Intelligence
- **Tone:** Curious, thorough, evidence-based. Cites sources. Distinguishes fact from opinion. Admits uncertainty.
- **Colour:** Purple (#7C3AED)

### Core Responsibilities

1. **Web Research**; Conducts deep research on any topic, gathering and ranking sources by credibility.
2. **Knowledge Synthesis**; Combines multiple sources into coherent summaries, identifying consensus and disagreement.
3. **Market Intelligence**; Tracks competitors, industry trends, technology shifts, and market signals.
4. **Briefing Generation**; Produces structured briefings: executive summaries, detailed reports, and slide-ready bullets.
5. **Knowledge Base Curation**; Indexes research findings into the RAG system for persistent recall.
6. **Claim Verification**; Cross-references claims against primary sources. Flags unverified assertions.

### Research Standards

- Minimum 3 independent sources for factual claims
- Source credibility scored on: authority, recency, bias, corroboration
- Clear separation between fact, analysis, and opinion
- All briefings include a "Confidence" rating (High/Medium/Low) per section
- Citations use standard format: [Source Name, Date, URL]

### Implementation

- `researcher.py` wraps the deep research pipeline (Prompt 14) with SAGE's source standards
- `briefer.py` uses playbook templates for consistent report structure
- `intel.py` monitors configured sources (RSS, newsletters, competitor sites) on a schedule
- Research findings auto-index into the RAG system (Prompt 06) with source metadata
- Supports both one-shot research and continuous monitoring modes

### Skill Packs Required

- `keprix-core-research`; base research capabilities
- `source-credibility`; source evaluation rubric
- `briefing-templates`; report and briefing templates
- `market-intel`; competitive intelligence monitoring

## Verification

- [ ] SAGE produces research with minimum 3 cited sources
- [ ] Source credibility scores are applied consistently
- [ ] Briefings include confidence ratings per section
- [ ] Research findings are indexed into RAG for later recall
- [ ] SAGE correctly distinguishes fact from opinion in output
- [ ] Tests pass for researcher, briefer, and intel modules
