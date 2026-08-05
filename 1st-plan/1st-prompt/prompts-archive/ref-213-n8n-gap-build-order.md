# n8n gap closure: build order and prompt map

Reference for prompts **207-212**. Source gap analysis:
`planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`.

## Build order

```
207 migrate from-n8n CLI
  |
  +---> 210 n8n sidecar MCP (docs cross-link)
  |
208 NL to playbook YAML
  |
211 expression sandbox (feeds 208 templates + 207 import placeholders)
  |
209 playbook run step I/O
  |
212 operator copilot (uses playbook + mutation + channel context)
```

| Order | Prompt | Title | Est. focus |
| --- | --- | --- | --- |
| 1 | 207 | n8n migrate CLI | Backend CLI + converter tests |
| 2 | 210 | n8n sidecar MCP | Docs + catalog UX (parallel with 207) |
| 3 | 211 | Expression sandbox | Security foundation for YAML |
| 4 | 208 | NL to playbook YAML | API + Start dialog + evals |
| 5 | 209 | Run step I/O detail | Frontend timeline |
| 6 | 212 | Operator copilot | Context bundle + drawer |

## Deferred (no prompt yet)

| Item | Reason |
| --- | --- |
| P6 Visual workflow canvas | Product pivot only; compile to `PlaybookGraph` if ever built |
| Git source control for playbooks | Enterprise tier |
| SSO / LDAP | Enterprise tier |
| Computer-use gateway | Hosted/Aiva tier |

## License boundary

Never merge code from `planning/competitor-research/agents-to-adopt/n8n/` into `src/keprix/`.
Read patterns only.

## Related shipped work

| Area | Prompt |
| --- | --- |
| Playbook runtime UI | 194 |
| MCP productivity pack | 172-175 |
| n8n MCP manifest | (pre-shipped in optional-mcps) |
