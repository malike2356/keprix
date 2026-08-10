from pathlib import Path


def test_postgres_idempotency_does_not_swallow_failed_transactions() -> None:
    root = Path(__file__).resolve().parents[2]
    migration = (
        root / "migrations" / "versions" / "032_document_vault_search_ops.py"
    ).read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS" in migration
    assert "except Exception" not in migration


def test_long_revision_widens_alembic_version_before_schema_changes() -> None:
    root = Path(__file__).resolve().parents[2]
    migration = (
        root / "migrations" / "versions" / "038_ai_transparency_generation_log.py"
    ).read_text(encoding="utf-8")

    widen = migration.index("ALTER COLUMN version_num TYPE VARCHAR(128)")
    table = migration.index("CREATE TABLE IF NOT EXISTS generation_log")

    assert widen < table


def test_usage_repair_is_idempotent_and_non_destructive() -> None:
    root = Path(__file__).resolve().parents[2]
    migration = (
        root / "migrations" / "versions" / "039_repair_llm_usage_events.py"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS llm_usage_events" in migration
    assert migration.count("CREATE INDEX IF NOT EXISTS") == 5
    assert "DROP TABLE" not in migration
