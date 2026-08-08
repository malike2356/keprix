# Compatibility and product pack migration

Legacy product packs under `/v1/products/{product_key}` remain. The Universal
Sidecar uses `/sidecar/v1/projects/{project_key}`.

| Product | Legacy | Universal adapter | Status |
| --- | --- | --- | --- |
| Carina | `/v1/products/carina` | `project_key=carina` with pack `carina-aiva-sidecar` | compatible |
| Aiva | `/v1/products/aiva` | wrapper_of=carina; surface grants only | compatible |
| Clinicom | domain-packs/clinicom http_app :3353 | migrate pack under `project_key=clinicom` | adapter_required |
| AbbiS | pending | `project_key=abbis` once pack installed | planned |
| Petraclus | pending | `project_key=petraclus` once pack installed | planned |
| Xeclone | pending | `project_key=xeclone` once pack installed | planned |
| Fleetz | pending | `project_key=fleetz` once pack installed | planned |

OpenAI-compatible `/v1/chat/*` is unchanged and separate.

Migration tip: keep southbound product APIs stable; map northbound clients to
`/sidecar/v1` while dual-running legacy paths during expand/migrate/contract.
