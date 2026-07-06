"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  fetchResearchPlaybooks,
  runResearchPlaybook,
  type ResearchPlaybookSpec,
} from "@/lib/research-workspace-api";

const PLAYBOOK_GUIDANCE: Record<string, { summary: string; recommended?: boolean }> = {
  pspp_analysis: {
    summary: "Prepare your dataset, run PSPP statistics, and capture outputs.",
    recommended: true,
  },
  jamovi_preparation: {
    summary: "Export a clean file and analysis plan for jamovi.",
    recommended: true,
  },
  survey_analysis: {
    summary: "Full survey workflow from import through descriptive stats to report draft.",
    recommended: true,
  },
  literature_review: {
    summary: "Import citations, extract claims, and draft a literature review.",
  },
  obsidian_research_map: {
    summary: "Map your Obsidian vault: clusters, orphans, and claim links.",
  },
  dataset_to_report: {
    summary: "Move from dataset through notebook analysis to a report draft.",
  },
};

type Props = {
  projectId: string;
  onRunComplete?: () => void;
};

export default function ResearchPlaybookRunner({ projectId, onRunComplete }: Props) {
  const [playbooks, setPlaybooks] = React.useState<ResearchPlaybookSpec[]>([]);
  const [playbookId, setPlaybookId] = React.useState("");
  const [dryRun, setDryRun] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetchResearchPlaybooks()
      .then((payload) => {
        const items = payload.items || [];
        const sorted = [...items].sort((left, right) => {
          const leftRec = PLAYBOOK_GUIDANCE[left.id]?.recommended ? 0 : 1;
          const rightRec = PLAYBOOK_GUIDANCE[right.id]?.recommended ? 0 : 1;
          return leftRec - rightRec || left.name.localeCompare(right.name);
        });
        setPlaybooks(sorted);
        const preferred =
          sorted.find((item) => item.id === "pspp_analysis") ||
          sorted.find((item) => item.id === "survey_analysis") ||
          sorted[0];
        if (preferred) {
          setPlaybookId(preferred.id);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const selected = playbooks.find((item) => item.id === playbookId);

  const onRun = async () => {
    if (!playbookId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runResearchPlaybook(playbookId, {
        project_id: projectId,
        dry_run: dryRun,
      });
      const pending = result.run.pending_approvals?.length || 0;
      setMessage(
        `${result.run.playbook_name} finished (${result.run.status}).` +
          (pending ? ` ${pending} step(s) need your review before results are final.` : ""),
      );
      onRunComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Workflow failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Guided workflows</Typography>
      <Typography variant="caption" color="text.secondary">
        Choose a step-by-step workflow. Recommended options are listed first for survey and statistics work.
      </Typography>
      <FormControl size="small" fullWidth>
        <InputLabel>Workflow</InputLabel>
        <Select label="Workflow" value={playbookId} onChange={(event) => setPlaybookId(event.target.value)}>
          {playbooks.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {PLAYBOOK_GUIDANCE[item.id]?.recommended ? `${item.name} (recommended)` : item.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {selected ? (
        <Typography variant="body2" color="text.secondary">
          {PLAYBOOK_GUIDANCE[selected.id]?.summary || selected.description}
        </Typography>
      ) : null}
      <FormControlLabel
        control={<Checkbox checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />}
        label="Practice run only (no files saved)"
      />
      <Button variant="contained" size="small" onClick={onRun} disabled={busy || !playbookId}>
        {busy ? "Running workflow..." : "Start workflow"}
      </Button>
      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}
    </Box>
  );
}
