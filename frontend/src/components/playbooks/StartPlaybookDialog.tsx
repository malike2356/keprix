"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import * as React from "react";
import {
  fetchPlaybookGraphs,
  startPlaybookRun,
  type PlaybookGraphTemplate,
} from "@/lib/playbook-api";

type StartPlaybookDialogProps = {
  open: boolean;
  onClose: () => void;
  templates: PlaybookGraphTemplate[];
  defaultGraphId?: string;
};

export default function StartPlaybookDialog({
  open,
  onClose,
  templates,
  defaultGraphId,
}: StartPlaybookDialogProps) {
  const router = useRouter();
  const [tab, setTab] = React.useState(0);
  const [graphId, setGraphId] = React.useState(defaultGraphId || "sdk-workflow");
  const [initialStateText, setInitialStateText] = React.useState("{}");
  const [advancedSpec, setAdvancedSpec] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setGraphId(defaultGraphId || templates[0]?.graph_id || "sdk-workflow");
    setInitialStateText("{}");
    setAdvancedSpec("");
    setError(null);
    setTab(0);
  }, [open, defaultGraphId, templates]);

  const selected = templates.find((item) => item.graph_id === graphId) || null;

  const handleSubmit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      let initial_state: Record<string, unknown> = {};
      try {
        initial_state = JSON.parse(initialStateText || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("Initial state must be valid JSON");
      }

      let body: Parameters<typeof startPlaybookRun>[0] = {
        graph_id: graphId,
        initial_state,
      };

      if (tab === 1 && advancedSpec.trim()) {
        const parsed = JSON.parse(advancedSpec) as {
          graph_id?: string;
          steps?: Array<Record<string, unknown>>;
          edges?: Array<Record<string, unknown>>;
          entry?: string;
          initial_state?: Record<string, unknown>;
        };
        body = {
          graph_id: parsed.graph_id || graphId,
          initial_state: parsed.initial_state || initial_state,
          steps: parsed.steps,
          edges: parsed.edges,
          entry: parsed.entry,
        };
      } else if (selected) {
        body = {
          graph_id: selected.graph_id,
          initial_state,
          steps: selected.steps,
          edges: selected.edges,
          entry: selected.entry || undefined,
        };
      }

      const run = await startPlaybookRun(body);
      onClose();
      router.push(`/playbooks/${run.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start playbook run");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Start playbook run</DialogTitle>
      <DialogContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
          <Tab label="Template" />
          <Tab label="Advanced JSON" />
        </Tabs>
        {tab === 0 ? (
          <Box sx={{ display: "grid", gap: 2 }}>
            <TextField
              select
              label="Playbook template"
              value={graphId}
              onChange={(event) => setGraphId(event.target.value)}
              fullWidth
            >
              {templates.map((template) => (
                <MenuItem key={template.graph_id} value={template.graph_id}>
                  {template.title}
                </MenuItem>
              ))}
            </TextField>
            {selected ? (
              <Typography variant="body2" color="text.secondary">
                {selected.description}
              </Typography>
            ) : null}
            <TextField
              label="Initial state (JSON)"
              value={initialStateText}
              onChange={(event) => setInitialStateText(event.target.value)}
              fullWidth
              multiline
              minRows={4}
            />
          </Box>
        ) : (
          <Box sx={{ display: "grid", gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Paste a full workflow spec JSON with graph_id, steps, edges, and optional entry.
            </Typography>
            <TextField
              label="Workflow spec JSON"
              value={advancedSpec}
              onChange={(event) => setAdvancedSpec(event.target.value)}
              fullWidth
              multiline
              minRows={10}
              placeholder='{"graph_id":"sdk-workflow","steps":[...],"edges":[...]}'
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={submitting} onClick={() => void handleSubmit()}>
          Start run
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function usePlaybookTemplates() {
  const [templates, setTemplates] = React.useState<PlaybookGraphTemplate[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    fetchPlaybookGraphs()
      .then((graphs) => {
        if (active) setTemplates(graphs);
      })
      .catch(() => {
        if (active) setTemplates([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { templates, loading };
}
