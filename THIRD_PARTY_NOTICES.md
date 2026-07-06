# Third-party notices

Legal compliance file only. Not linked from the Keprix application UI.

## Incorporated source codebases

### Hermes Agent - Nous Research

**Upstream:** Hermes Agent by Nous Research
**Repository:** https://github.com/nousresearch/hermes-agent
**Scope:** Keprix's CLI runtime (the interactive REPL, toolset dispatch, bootstrap layer,
skill loader, and terminal interface) was forked from Hermes Agent, renamed from `hermes`
to `keprix`, and substantially extended. The workspace layer, operator dashboard,
multi-tenancy, governance, and all features described in the Keprix documentation are
original Keprix design built above the CLI foundation.

MIT Licence text:

Copyright (c) 2025 Nous Research

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

An additional 20 open-source agent frameworks informed Keprix's design through research
and pattern analysis. No source code from these projects was incorporated into Keprix.
See docs/community/acknowledgments.md for the full list and the specific design areas
each project informed.

## Python dependencies

Generate the full list from the project virtualenv:

```bash
pip install pip-licenses
pip-licenses --format=markdown > /tmp/keprix-python-licenses.md
```

Notable stacks: FastAPI, SQLAlchemy, Pydantic, httpx, cryptography, uvicorn.

## Node.js dependencies

Generate from the frontend workspace:

```bash
cd frontend && pnpm licenses list --json
```

Notable stacks: Next.js, React, Material UI, SWR.
