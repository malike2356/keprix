"""Database tool adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterResult, ToolAdapter


class DatabaseAdapter(ToolAdapter):
    category = "databases"
    risk_level = "high"
    requires_approval_for_write = True
    supports_dry_run = True
    driver: str = ""

    def __init__(self, *, name: str, env_key: str, driver: str) -> None:
        self.name = name
        self.driver = driver
        self.required_env = (env_key,)
        self.setup_doc = f"Set {env_key} with a read-only connection string."

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        if action == "query":
            sql = str(params.get("sql") or "").strip()
            if not sql.lower().startswith("select"):
                return AdapterResult(ok=False, error="Only SELECT queries are allowed by default")
            return AdapterResult(
                ok=True,
                data={"sql": sql, "rows": [], "driver": self.driver, "read_only": True},
            )
        return AdapterResult(ok=False, error=f"Unsupported action: {action}")


DATABASE_ADAPTERS: list[ToolAdapter] = [
    DatabaseAdapter(name="mysql", env_key="MYSQL_READONLY_URL", driver="mysql"),
    DatabaseAdapter(name="snowflake", env_key="SNOWFLAKE_READONLY_URL", driver="snowflake"),
    DatabaseAdapter(name="databricks", env_key="DATABRICKS_READONLY_URL", driver="databricks"),
    DatabaseAdapter(name="couchbase", env_key="COUCHBASE_READONLY_URL", driver="couchbase"),
    DatabaseAdapter(name="singlestore", env_key="SINGLESTORE_READONLY_URL", driver="singlestore"),
]
