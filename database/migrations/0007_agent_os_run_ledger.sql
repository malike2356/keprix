CREATE TABLE IF NOT EXISTS agent_os_run_ledger (
  entry_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  status TEXT NOT NULL,
  input_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  eval_score DOUBLE PRECISION,
  tokens INTEGER NOT NULL DEFAULT 0,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  user_corrections JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_os_run_ledger_source
  ON agent_os_run_ledger (source_type, source_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_os_run_ledger_workspace
  ON agent_os_run_ledger (workspace_id, created_at DESC);
