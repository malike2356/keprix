# Keprix agent handoff

## 2026-09-20: claim tests + installer Python guard

- **Git tip:** pending push
- **Finding:** marketed curl install failed on Ubuntu 22.04 Python 3.10
- **Fix:** install.sh requires 3.11/3.12 before clone; marketing copy updated
- **Virtual proof:** Ubuntu 22.04 + python3.11 -> keprix 0.16.0; module imports PASS
- **Report:** archive/workspace-audits/2026-09-20-keprix-claim-virtual-tests.md

