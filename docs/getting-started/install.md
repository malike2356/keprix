# Install Keprix

Use `pipx` for a normal workstation install. It gives Keprix its own isolated Python environment and exposes the `keprix` command globally.

## Requirements

- Python 3.11 or 3.12
- pipx
- At least one LLM provider key for agent replies

Install pipx if needed:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Restart your shell after `ensurepath` if `pipx` is not immediately available.

## Install from a release

```bash
pipx install 'keprix[tui]'
keprix --version
keprix start --host 127.0.0.1 --port 3333
```

In another terminal:

```bash
keprix tui
```

Use `keprix tui --help` to see terminal UI flags such as session resume, model override, API URL, bearer token, and mouse capture.

## Install from a local checkout

From the repository root:

```bash
pipx install '.[tui]' --force
keprix --version
keprix tui --help
```

Use this when testing a local build before publishing a release.

## Voice extras

The terminal UI can use push-to-talk voice capture with the voice extra:

```bash
pipx install 'keprix[tui-voice]'
```

From a checkout:

```bash
pipx install '.[tui-voice]' --force
```

## Contributor install

Use a repository virtual environment only when changing Keprix itself:

```bash
bash scripts/install.sh
source .venv/bin/activate
```

Normal users should not need `PYTHONPATH`, an activated development venv, or manual module entry points to run `keprix tui`.
