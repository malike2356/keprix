from pathlib import Path


def test_backend_entrypoint_runs_migrations_before_api() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "docker" / "keprix-backend-entrypoint.sh").read_text(encoding="utf-8")

    migration = script.index("gosu keprix alembic upgrade head")
    process = script.index('exec gosu keprix "$@"')

    assert migration < process
    assert 'KEPRIX_RUN_MIGRATIONS:-true' in script
