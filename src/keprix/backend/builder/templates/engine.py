"""Template scaffolding engine (Prompt 29)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from keprix.backend.builder.schemas import FLEETX_DOMAINS, TEMPLATE_NAMES

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def list_templates() -> list[dict[str, Any]]:
    rows = []
    for name in TEMPLATE_NAMES:
        manifest = _manifest(name)
        rows.append(
            {
                "name": name,
                "description": manifest.get("description", ""),
                "files": manifest.get("files", []),
                "implemented": (TEMPLATES_DIR / name).exists(),
            }
        )
    return rows


def template_details(name: str) -> dict[str, Any]:
    if name not in TEMPLATE_NAMES:
        raise ValueError(f"Unknown template: {name}")
    manifest = _manifest(name)
    template_dir = TEMPLATES_DIR / name
    files = []
    if template_dir.exists():
        for path in sorted(template_dir.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                files.append(str(path.relative_to(template_dir)))
    return {"name": name, **manifest, "files": files or manifest.get("files", [])}


def scaffold_project(
    *,
    template: str,
    name: str,
    path: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if template not in TEMPLATE_NAMES:
        raise ValueError(f"Unknown template: {template}")
    target = Path(path).resolve() / name
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"Target path already exists and is not empty: {target}")

    if template == "keprix-nextjs-app":
        _scaffold_keprix_nextjs(target, name, config or {})
    else:
        _scaffold_minimal(target, template, name, config or {})

    install_log = _run_install(target, template)
    return {"path": str(target), "template": template, "name": name, "install_log": install_log}


def _manifest(name: str) -> dict[str, Any]:
    path = TEMPLATES_DIR / name / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"description": f"{name} scaffold", "files": []}


def _write(target: Path, relative: str, content: str) -> None:
    dest = target / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


def _domains_ts(project_name: str, config: dict[str, Any]) -> str:
    domains = config.get("domains")
    if not domains and project_name.lower() == "fleetx":
        domains = [{"name": name, "fields": fields} for name, fields in FLEETX_DOMAINS]
    if not domains:
        domains = [{"name": "Example", "fields": ["id", "name"]}]
    lines = ["export const registeredDomains = ["]
    for domain in domains:
        fields = ", ".join(f'"{field}"' for field in domain["fields"])
        lines.append(f'  {{ name: "{domain["name"]}", fields: [{fields}] }},')
    lines.append("] as const;")
    lines.append("")
    lines.append("export type DomainName = (typeof registeredDomains)[number]['name'];")
    return "\n".join(lines) + "\n"


def _scaffold_keprix_nextjs(target: Path, name: str, config: dict[str, Any]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    _write(
        target,
        "package.json",
        json.dumps(
            {
                "name": name,
                "private": True,
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "lint": "next lint"},
                "dependencies": {
                    "next": "14.2.5",
                    "react": "18.3.1",
                    "react-dom": "18.3.1",
                    "@keprix-ai/sdk": "file:../../../sdk/typescript",
                },
                "devDependencies": {
                    "typescript": "5.5.4",
                    "@types/node": "20.14.10",
                    "@types/react": "18.3.3",
                    "@types/react-dom": "18.3.0",
                },
            },
            indent=2,
        )
        + "\n",
    )
    _write(
        target,
        "tsconfig.json",
        json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2020",
                    "lib": ["dom", "dom.iterable", "es2020"],
                    "allowJs": True,
                    "skipLibCheck": True,
                    "strict": True,
                    "noEmit": True,
                    "module": "esnext",
                    "moduleResolution": "bundler",
                    "jsx": "preserve",
                    "incremental": True,
                    "paths": {"@/*": ["./src/*"]},
                },
                "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
                "exclude": ["node_modules"],
            },
            indent=2,
        )
        + "\n",
    )
    _write(target, "next.config.mjs", "export default { reactStrictMode: true };\n")
    _write(
        target,
        "src/keprix/client.ts",
        "import { KeprixClient } from '@keprix-ai/sdk';\n\n"
        "export const keprix = new KeprixClient({\n"
        "  baseUrl: process.env.NEXT_PUBLIC_KEPRIX_URL || 'http://localhost:8000',\n"
        "  apiKey: process.env.KEPRIX_API_KEY || '',\n"
        "});\n",
    )
    _write(target, "src/keprix/domains.ts", _domains_ts(name, config))
    _write(
        target,
        "src/app/layout.tsx",
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return (\n"
        "    <html lang=\"en\">\n"
        "      <body>{children}</body>\n"
        "    </html>\n"
        "  );\n"
        "}\n",
    )
    _write(
        target,
        "src/app/page.tsx",
        "import { registeredDomains } from '@/keprix/domains';\n\n"
        "export default function HomePage() {\n"
        "  return (\n"
        "    <main style={{ padding: 24 }}>\n"
        f"      <h1>{name}</h1>\n"
        "      <p>Built on keprix SDK with pre-registered domain entities.</p>\n"
        "      <ul>\n"
        "        {registeredDomains.map((domain) => (\n"
        "          <li key={domain.name}>{domain.name}: {domain.fields.join(', ')}</li>\n"
        "        ))}\n"
        "      </ul>\n"
        "    </main>\n"
        "  );\n"
        "}\n",
    )
    _write(
        target,
        ".env.example",
        "NEXT_PUBLIC_KEPRIX_URL=http://localhost:8000\nKEPRIX_API_KEY=\n",
    )
    _write(
        target,
        "README.md",
        f"# {name}\n\nNext.js app scaffolded with keprix SDK integration.\n\n"
        "Run `npm install` then `npm run dev`.\n",
    )
    _write(
        target,
        "manifest.json",
        json.dumps({"description": "Next.js app with @keprix-ai/sdk and domain registration", "files": []}, indent=2)
        + "\n",
    )


def _scaffold_minimal(target: Path, template: str, name: str, config: dict[str, Any]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    _write(target, "README.md", f"# {name}\n\nScaffolded from template `{template}`.\n")
    if template.startswith("custom-php") or template in {"laravel-api", "wordpress-theme", "wordpress-plugin"}:
        (target / "includes").mkdir(exist_ok=True)
        (target / "modules").mkdir(exist_ok=True)
        (target / "database").mkdir(exist_ok=True)
        _write(target, "index.php", "<?php\n// Entry point\n")
    elif template == "fastapi-service":
        _write(target, "main.py", "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'ok': True}\n")
        _write(target, "requirements.txt", "fastapi\nuvicorn\n")
    else:
        _write(target, "package.json", json.dumps({"name": name, "private": True, "version": "0.1.0"}, indent=2) + "\n")


def _run_install(target: Path, template: str) -> str:
    if template == "keprix-nextjs-app" and (target / "package.json").exists():
        try:
            proc = subprocess.run(
                ["npm", "install", "--ignore-scripts"],
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=120,
            )
            return ((proc.stdout or "") + (proc.stderr or "")).strip()[:4000]
        except Exception as exc:
            return str(exc)
    if template in {"laravel-api", "custom-php-mvc"} and shutil_which("composer"):
        try:
            proc = subprocess.run(["composer", "install", "--no-interaction"], cwd=str(target), capture_output=True, text=True, timeout=120)
            return ((proc.stdout or "") + (proc.stderr or "")).strip()[:4000]
        except Exception as exc:
            return str(exc)
    return "install skipped"


def shutil_which(cmd: str) -> bool:
    import shutil

    return shutil.which(cmd) is not None
