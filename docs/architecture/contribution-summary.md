# Contribution summary

What this repository adds on top of its upstream base, where the evidence for each
claim lives, how to verify it, and what is not claimed.

## The upstream boundary

Keprix is a derivative work of [Hermes Agent](https://github.com/nousresearch/hermes-agent)
by Nous Research, MIT licensed. From upstream: the CLI runtime, the interactive REPL,
the tool dispatch mechanism, the bootstrap layer, and the skill architecture.

**The exact fork point cannot be determined from git history, and that is stated
here rather than guessed.** This repository's git history has no merge base with
`github.com/nousresearch/hermes-agent`: a direct fetch of 50 commits of upstream
history found no common ancestor (`git merge-base HEAD upstream/main` returns
nothing). The earliest commits in this repository's own history show Hermes being
adopted by import and rename rather than by a `git fork` with shared commit
history:

```
$ git log --oneline --reverse | head -2
5ac3e618 feat(foundation): initial Keprix architecture and scaffold
10c60d0d feat(foundation): adopt Hermes as Keprix backbone, complete rename
```

`10c60d0d` is the commit that brings in the Hermes codebase under the Keprix name.
There is no recorded upstream commit SHA or tag this was taken from.

## What was added

| Area | The claim | Where the evidence is |
|---|---|---|
| Human-approved self-modification | Mutations are proposals requiring four-eyes approval, applied only through a reversible mount lifecycle. No path in this codebase applies a change unapproved. | `src/keprix/mutation/` (28 tracked files), `docs/architecture/mutation-as-mount.md`, tests under `tests/mutation/` |
| Non-mutable safety floor | Soft Wall, tenant row-level security, Channel Shield, the document vault, billing, auth and governance are explicitly listed as targets the mutation-mount path refuses to touch, by id and by path substring. | `src/keprix/mutation/mount/banned.py` (`BANNED_TARGET_IDS`, `BANNED_SUBSTRINGS`, `BANNED_PROVIDER_IDS`) |
| Reversibility | Disabling a plugin unmounts tools, prompt sections, MCP bindings and seam providers in-process, without deleting files. | `src/keprix/plugin_lifecycle/`, `docs/architecture/reversible-plugin-lifecycle.md`, `src/keprix/tests/plugin_lifecycle/test_reversible_lifecycle.py` |
| Multi-tenant isolation | One workspace cannot read another's data. | `docs/features/tenant-isolation.md`, `tests/tenancy/` |
| Credential vault | Secrets handling as a seam-level floor. | `src/keprix/vault/`, `tests/vault/` |
| Channel Shield | Inbound-channel protection (Telegram, WhatsApp, etc.) as a seam-level floor, not a per-call check. | `src/keprix/channel_shield/`, `tests/channel_shield/` |

## How to verify it

Installed from a checkout (Python 3.11 or 3.12 required):

```bash
pipx install '.[tui]' --force
```

Full test suite entry point: `scripts/run_tests.sh` (per-file process isolation,
hermetic `HERMES_HOME`/credential-env sandboxing - see `tests/conftest.py`). The
commands below were run directly against the subsets this document makes claims
about, from a clean checkout at commit `2305b286` on `main`, using the repository's
own `.venv`.

**Mutation engine:**

```
$ .venv/bin/python -m pytest tests/mutation/ -q
........................................................................ [ 49%]
........................................................................ [ 98%]
..                                                                       [100%]
146 passed, 2 warnings in 106.44s (0:01:46)
```

**Reversible plugin lifecycle:**

```
$ .venv/bin/python -m pytest src/keprix/tests/plugin_lifecycle/ -q
.....                                                                    [100%]
5 passed in 0.18s
```

**Tenant isolation:**

```
$ .venv/bin/python -m pytest tests/tenancy/ -q
...............                                                          [100%]
15 passed in 0.19s
```

**Channel Shield:**

```
$ .venv/bin/python -m pytest tests/channel_shield/ -q
................................                                         [100%]
32 passed, 2 warnings in 6.07s
```

**Credential vault:**

```
$ .venv/bin/python -m pytest tests/vault/ -q
.............                                                            [100%]
13 passed, 2 warnings in 6.09s
```

## Measured numbers

All counts are from `git ls-files` against the tracked tree at commit `2305b286`,
not an estimate.

| What | Command | Result |
|---|---|---|
| Total tracked files in the repository | `git ls-files \| wc -l` | 10,887 |
| Total tracked files under `tests/` | `git ls-files tests/ \| wc -l` | 1,033 |
| Tracked files under `src/keprix/mutation/` | `git ls-files src/keprix/mutation/ \| wc -l` | 28 |
| Tracked files under `tests/mutation/` | `git ls-files tests/mutation/ \| wc -l` | 26 |
| Mutation-related test files anywhere under `tests/` (includes `tests/api/`, `tests/frontend/`, `tests/integration/` mutation coverage, not only `tests/mutation/`) | `git ls-files tests/ \| grep -i mutation \| wc -l` | 32 |

## What is not claimed

- No paying customers.
- No production deployments.
- No published benchmarks.
- No third-party security audit.
- No certification of any kind.

## Why it matters

A system that can propose changes to its own behaviour needs a boundary that
decides which changes are reversible, which are forbidden outright, and who signs
off on the rest. The question behind this build is who decides that boundary was
drawn correctly, on what evidence, and what survives the decision once the system
has been running and changing itself for a while. The test suites above are the
current evidence for where that boundary sits in this implementation; they are not
a claim that the boundary is correctly drawn, only that it exists, is tested, and
is enforced in code rather than only in documentation.
