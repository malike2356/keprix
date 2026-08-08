# Memory and files

## Memory modes (manifest)

| Mode | Behaviour |
| --- | --- |
| `disabled` | No durable or ephemeral memory |
| `ephemeral` | Session-scoped only (default for demos) |
| `project_facts` | Project-scoped durable facts |
| `subject` | Subject / entity scoped |
| `shared_approved` | Shared only after explicit approval |

Namespaces always include project, deployment, tenant, subject, pack, and
retention class. Cross-project retrieval is impossible by construction.

## Data minimisation

Products send purpose-limited context slices, not entire records by default.
Sensitive fields are excluded from prompts unless a capability explicitly
requires them and policy permits. Logs contain ids and classifications, not raw
secrets or regulated text.

Every generated fact stores provenance, source record/version, timestamp,
model/version where relevant, confidence, verification, and expiry.

Product deletion and retention events must propagate to Keprix indexes, caches,
jobs, artifacts, and memory with auditable completion.

## Files

The `files` scope is high-risk. File APIs (when enabled) enforce size limits,
content-type allowlists, and tenant isolation. Prefer artifact references over
embedding large blobs in prompts.
