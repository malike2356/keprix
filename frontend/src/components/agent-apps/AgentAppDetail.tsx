"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import * as React from "react";
import useSWR from "swr";
import AgentAppEvalsPanel from "@/components/agent-apps/AgentAppEvalsPanel";
import AgentAppOutput from "@/components/agent-apps/AgentAppOutput";
import AgentAppRunForm, {
  initialFormValues,
  validateAgentAppForm,
} from "@/components/agent-apps/AgentAppRunForm";
import AgentAppRunHistory from "@/components/agent-apps/AgentAppRunHistory";
import {
  fetchAgentAppReadiness,
  fetchAgentAppRun,
  runAgentApp,
  type AgentAppDetail,
  type AgentAppRunSummary,
} from "@/lib/agent-apps-api";

type Props = {
  appName: string;
  app?: AgentAppDetail;
};

function applyRunInputs(
  app: AgentAppDetail | undefined,
  run: AgentAppRunSummary,
  setValues: React.Dispatch<React.SetStateAction<Record<string, string>>>,
  setLegacyInput: React.Dispatch<React.SetStateAction<string>>,
) {
  if (!app?.inputs?.length) {
    return;
  }
  fetchAgentAppRun(run.trace_id)
    .then((detail) => {
      const input = detail.run.input ?? {};
      const text = typeof input.input === "string" ? input.input : "";
      if (text) {
        setLegacyInput(text);
      }
      const context = input.context;
      if (context && typeof context === "object" && "form" in context) {
        const form = (context as { form?: Record<string, string> }).form;
        if (form) {
          setValues((prev) => ({ ...prev, ...form }));
        }
      }
    })
    .catch(() => undefined);
}

export default function AgentAppDetail({ appName, app }: Props) {
  const [tab, setTab] = React.useState(0);
  const [values, setValues] = React.useState(() => initialFormValues(app?.inputs));
  const [legacyInput, setLegacyInput] = React.useState("world");
  const [result, setResult] = React.useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const { data: readiness } = useSWR(["agent-readiness", appName], () => fetchAgentAppReadiness(appName));

  React.useEffect(() => {
    setValues(initialFormValues(app?.inputs));
    setFieldErrors({});
    setResult(null);
  }, [app?.inputs, appName]);

  const hasForm = Boolean(app?.inputs?.length);
  const canRun = readiness?.ready !== false;

  const onRun = async () => {
    if (hasForm && app?.inputs) {
      const validation = validateAgentAppForm(app.inputs, values);
      setFieldErrors(validation);
      if (Object.keys(validation).length) {
        return;
      }
    }

    setBusy(true);
    setError(null);
    try {
      const response = await runAgentApp(appName, {
        input: hasForm ? "" : legacyInput,
        inputs: hasForm ? values : undefined,
      });
      setResult(response.result as Record<string, unknown>);
      setTab(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  };

  const onRerun = (run: AgentAppRunSummary) => {
    applyRunInputs(app, run, setValues, setLegacyInput);
    setTab(0);
  };

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={app?.runtime || "python"} size="small" />
        {app?.category ? <Chip label={app.category} size="small" variant="outlined" /> : null}
        <Chip label={`v${app?.version || "?"}`} size="small" variant="outlined" />
      </Stack>

      <Tabs value={tab} onChange={(_event, value) => setTab(value)}>
        <Tab label="Run" />
        <Tab label="History" />
        <Tab label="Evals" />
      </Tabs>

      {tab === 0 ? (
        <>
          {readiness && !readiness.ready ? (
            <Alert severity="warning">
              {readiness.missing_env.length ? (
                <>
                  Missing secrets: {readiness.missing_env.join(", ")}.{" "}
                  {readiness.vault_links[0] ? (
                    <Button size="small" href={readiness.vault_links[0].href}>
                      Open Vault
                    </Button>
                  ) : null}
                </>
              ) : null}
              {readiness.missing_permissions.length ? (
                <Box sx={{ mt: readiness.missing_env.length ? 1 : 0 }}>
                  Missing permissions: {readiness.missing_permissions.join(", ")}.{" "}
                  <Button size="small" href={readiness.permission_links?.[0]?.href || "/settings"}>
                    Open Settings
                  </Button>
                </Box>
              ) : null}
            </Alert>
          ) : null}

          {hasForm && app?.inputs ? (
            <AgentAppRunForm
              inputs={app.inputs}
              values={values}
              onChange={setValues}
              errors={fieldErrors}
              disabled={busy}
            />
          ) : (
            <TextField
              label="Input"
              value={legacyInput}
              onChange={(e) => setLegacyInput(e.target.value)}
              size="small"
              fullWidth
              disabled={busy}
            />
          )}

          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={onRun}
            disabled={busy || !canRun}
            sx={{ alignSelf: "flex-start" }}
          >
            {busy ? "Running..." : "Run now"}
          </Button>

          {error ? <Alert severity="error">{error}</Alert> : null}
          <AgentAppOutput app={app} result={result} />
        </>
      ) : null}

      {tab === 1 ? <AgentAppRunHistory appName={appName} onRerun={onRerun} /> : null}
      {tab === 2 ? <AgentAppEvalsPanel appName={appName} evalSuite={app?.eval_suite} /> : null}
    </Box>
  );
}
