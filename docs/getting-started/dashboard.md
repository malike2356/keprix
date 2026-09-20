# Local web dashboard

The Keprix workspace runs **on your machine**. There is no hosted product at
`app.keprixai.com` — that hostname redirects to [keprixai.com/docs](https://keprixai.com/docs).
After you install the CLI, start the dashboard locally.

## Foreground (this terminal)

```bash
keprix dashboard
```

The CLI prints a READY line with:

| Surface | Default URL |
| --- | --- |
| Next.js UI | `http://127.0.0.1:9120/home` |
| FastAPI backend | `http://127.0.0.1:9119` |

Foreground mode binds loopback, starts (or attaches to) the backend, and opens
the UI in a browser. Closing the terminal stops that process unless a service
is also installed.

Use `--no-open` if you do not want a browser window. Use `--port 0` to let the
OS assign the backend port.

## Persist across logout (recommended)

Same pattern as `keprix gateway install`. This writes a user systemd unit
(`keprix-dashboard.service` on Linux) or a launchd job (macOS), enables linger,
and pins the UI port so the URL stays stable:

```bash
keprix dashboard install
keprix dashboard status
```

Open **http://127.0.0.1:9120/home**. The unit runs:

```text
python -m keprix_cli.main dashboard --host 127.0.0.1 --port 9119 --no-open
```

with `KEPRIX_DASHBOARD_SERVICE=1` and `KEPRIX_DASHBOARD_FRONTEND_PORT=9120`.

| Command | What it does |
| --- | --- |
| `keprix dashboard install` | Write, enable, and start the user service |
| `keprix dashboard status` | systemd / launchd unit status |
| `keprix dashboard start` / `stop` / `restart` | Control the installed unit |
| `keprix dashboard uninstall` | Remove the unit |

`--stop` and `--status` (flags on `keprix dashboard`, not subcommands) still
scan the process table for a stray foreground dashboard. They do **not** manage
the installed unit. Use `keprix dashboard stop` / `status` for the service.

On Linux, `loginctl enable-linger "$USER"` is applied so the unit survives
logout. Rebuild the frontend on first install if `frontend/.next/standalone`
is missing.

## Docker Compose (optional)

Compose still exposes the full stack at `http://127.0.0.1:3000` (UI) and
`http://127.0.0.1:3333` (API) **on the machine where you run Docker**. That is
not the Contabo marketing host, and it is not required for the CLI dashboard.

See [Quickstart](quickstart.md) Option B.

## Health checks

```bash
# CLI dashboard (service or foreground)
curl -sI http://127.0.0.1:9120/home
curl -sI http://127.0.0.1:9119/

# Docker Compose only
curl -s http://127.0.0.1:3333/api/health
```

Expect UI `200`. Loopback backend often returns `302` to the SPA on `/`; that
is normal. Do not probe `https://app.keprixai.com/api/health` — there is no
public API there.

## Related

- [Install](install.md)
- [First run](first-run.md)
- [CLI reference](../reference/cli.md)
- [Admin dashboard](../operations/admin-dashboard.md) (in-app `/dashboard` after you are signed in)
- [keprixai.com origin](../operations/keprixai-com-origin.md)
