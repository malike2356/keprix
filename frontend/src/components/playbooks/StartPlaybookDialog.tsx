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
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import { draftPlaybookFromPrompt } from "@/lib/playbook-draft-api";
import {
  fetchPlaybookGraphs,
  startPlaybookRun,
  type PlaybookGraphTemplate,
} from "@/lib/playbook-api";
import {
  decompileStudioYaml,
  saveStudioCanvas,
} from "@/lib/playbook-studio/playbook-studio-api";

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
  const [describePrompt, setDescribePrompt] = React.useState("");
  const [generatedYaml, setGeneratedYaml] = React.useState("");
  const [draftWarnings, setDraftWarnings] = React.useState<string[]>([]);
  const [draftRunSpec, setDraftRunSpec] = React.useState<Record<string, unknown> | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [generating, setGenerating] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setGraphId(defaultGraphId || templates[0]?.graph_id || "sdk-workflow");
    setInitialStateText("{}");
    setAdvancedSpec("");
    setDescribePrompt("");
    setGeneratedYaml("");
    setDraftWarnings([]);
    setDraftRunSpec(null);
    setError(null);
    setTab(0);
  }, [open, defaultGraphId, templates]);

  const selected = templates.find((item) => item.graph_id === graphId) || null;

  const handleGenerateYaml = async () => {
    setError(null);
    setGenerating(true);
    try {
      const draft = await draftPlaybookFromPrompt({
        prompt: describePrompt.trim(),
        template_hint: graphId,
      });
      setGeneratedYaml(draft.yaml_text);
      setDraftWarnings(draft.warnings || []);
      setDraftRunSpec(draft.run_spec as Record<string, unknown>);
      setGraphId(draft.playbook_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate playbook YAML");
    } finally {
      setGenerating(false);
    }
  };

  const handleEditInAdvanced = () => {
    if (!draftRunSpec) return;
    setAdvancedSpec(JSON.stringify(draftRunSpec, null, 2));
    setTab(2);
  };

  const handleOpenInStudio = async () => {
    if (!generatedYaml) return;
    setError(null);
    setSubmitting(true);
    try {
      const { canvas } = await decompileStudioYaml(generatedYaml);
      const studioId = String(draftRunSpec?.graph_id || canvas.id || graphId || "draft_playbook");
      await saveStudioCanvas(studioId, { ...canvas, id: studioId });
      onClose();
      router.push(`/playbooks/studio/${encodeURIComponent(studioId)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open playbook in Studio");
    } finally {
      setSubmitting(false);
    }
  };

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

      if (tab === 2 && advancedSpec.trim()) {
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
      } else if (tab === 1) {
        if (!draftRunSpec) {
          throw new Error("Generate playbook YAML before starting a run");
        }
        body = {
          graph_id: String(draftRunSpec.graph_id || graphId),
          initial_state,
          steps: draftRunSpec.steps as Array<Record<string, unknown>>,
          edges: draftRunSpec.edges as Array<Record<string, unknown>>,
          entry: typeof draftRunSpec.entry === "string" ? draftRunSpec.entry : undefined,
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
          <Tab label="Describe" />
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
        ) : null}
        {tab === 1 ? (
          <Box sx={{ display: "grid", gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Describe the playbook you want in plain language. Keprix generates editable YAML
              using Keprix step references such as {"{{ steps.step_id.output }}"}.
            </Typography>
            <TextField
              label="Playbook description"
              value={describePrompt}
              onChange={(event) => setDescribePrompt(event.target.value)}
              fullWidth
              multiline
              minRows={4}
              placeholder="Every morning, fetch unread email and post a digest note"
            />
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Button
                variant="outlined"
                disabled={generating || !describePrompt.trim()}
                onClick={() => void handleGenerateYaml()}
              >
                {generating ? "Generating..." : "Generate YAML"}
              </Button>
              <Button variant="text" disabled={!draftRunSpec} onClick={handleEditInAdvanced}>
                Edit in Advanced
              </Button>
              <Button
                variant="text"
                disabled={!generatedYaml || submitting}
                onClick={() => void handleOpenInStudio()}
              >
                Open in Studio
              </Button>
            </Box>
            {draftWarnings.length ? (
              <Alert severity="warning">
                {draftWarnings.map((warning) => (
                  <Typography key={warning} variant="body2">
                    {warning}
                  </Typography>
                ))}
              </Alert>
            ) : null}
            {generatedYaml ? (
              <CodeBlock language="yaml" content={generatedYaml} />
            ) : null}
            <TextField
              label="Initial state (JSON)"
              value={initialStateText}
              onChange={(event) => setInitialStateText(event.target.value)}
              fullWidth
              multiline
              minRows={3}
            />
          </Box>
        ) : null}
        {tab === 2 ? (
          <Box sx={{ display: "grid", gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Paste a full playbook run spec JSON with graph_id, steps, edges, and optional entry.
            </Typography>
            <TextField
              label="Playbook run spec JSON"
              value={advancedSpec}
              onChange={(event) => setAdvancedSpec(event.target.value)}
              fullWidth
              multiline
              minRows={10}
              placeholder='{"graph_id":"daily-digest","steps":[...],"edges":[...]}'
            />
          </Box>
        ) : null}
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
