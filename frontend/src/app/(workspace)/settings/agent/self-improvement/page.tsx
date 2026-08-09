"use client";

import SaveIcon from "@mui/icons-material/Save";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Settings = {
  watch_sessions: boolean;
  propose_at_occurrences: number;
  min_confidence: number;
  auto_create_skills: boolean;
  auto_apply_improvements: boolean;
  weekly_report_schedule: string;
  ignored_pattern_keywords: string[];
};

const defaults: Settings = {
  watch_sessions: true,
  propose_at_occurrences: 3,
  min_confidence: 0.7,
  auto_create_skills: false,
  auto_apply_improvements: false,
  weekly_report_schedule: "0 9 * * 1",
  ignored_pattern_keywords: [],
};

export default function SelfImprovementSettingsPage() {
  const [settings, setSettings] = React.useState<Settings>(defaults);
  const [keywords, setKeywords] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    void (async () => {
      const response = await ceApi("/api/agent-os/settings/self-improvement");
      if (!response.ok) return;
      const payload = (await response.json()) as { settings: Settings };
      setSettings(payload.settings);
      setKeywords(payload.settings.ignored_pattern_keywords.join(", "));
    })();
  }, []);

  const save = async () => {
    const payload = {
      ...settings,
      ignored_pattern_keywords: keywords.split(",").map((item) => item.trim()).filter(Boolean),
    };
    const response = await ceApi("/api/agent-os/settings/self-improvement", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setMessage(response.ok ? "Settings saved." : "Save failed.");
  };

  return (
    <Box sx={{ display: "grid", gap: 3, maxWidth: 840 }}>
      <PageHeader
        title="Self-improvement"
        description="Control session pattern detection and skill improvement proposals. Soft Wall still wins for production apply; review proposals in Agent OS Improvements."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Agent" },
          { label: "Self-improvement" },
        ]}
        actions={
          <Button component="a" href="/agent-os/improvements" variant="outlined" size="small">
            Review improvement proposals
          </Button>
        }
      />
      <Alert severity="info">
        Auto-apply settings never bypass Soft Wall review at `/agent-os/improvements` for production
        workspaces.
      </Alert>
      <FormControlLabel
        control={<Checkbox checked={settings.watch_sessions} onChange={(event) => setSettings({ ...settings, watch_sessions: event.target.checked })} />}
        label="Watch sessions for repeated task patterns"
      />
      <Typography variant="body2">Propose at {settings.propose_at_occurrences}+ occurrences</Typography>
      <Slider
        value={settings.propose_at_occurrences}
        min={2}
        max={20}
        step={1}
        valueLabelDisplay="auto"
        onChange={(_, value) => setSettings({ ...settings, propose_at_occurrences: Array.isArray(value) ? value[0] : value })}
      />
      <Typography variant="body2">Minimum confidence {Math.round(settings.min_confidence * 100)}%</Typography>
      <Slider
        value={settings.min_confidence}
        min={0}
        max={1}
        step={0.05}
        valueLabelDisplay="auto"
        onChange={(_, value) => setSettings({ ...settings, min_confidence: Array.isArray(value) ? value[0] : value })}
      />
      <FormControlLabel
        control={<Checkbox checked={settings.auto_create_skills} onChange={(event) => setSettings({ ...settings, auto_create_skills: event.target.checked })} />}
        label="Auto-create skills from approved proposals"
      />
      <FormControlLabel
        control={<Checkbox checked={settings.auto_apply_improvements} onChange={(event) => setSettings({ ...settings, auto_apply_improvements: event.target.checked })} />}
        label="Auto-apply skill improvements"
      />
      <TextField
        label="Weekly report schedule"
        value={settings.weekly_report_schedule}
        onChange={(event) => setSettings({ ...settings, weekly_report_schedule: event.target.value })}
      />
      <TextField label="Ignored keywords" value={keywords} onChange={(event) => setKeywords(event.target.value)} />
      <Button sx={{ width: "fit-content" }} variant="contained" startIcon={<SaveIcon />} onClick={() => void save()}>
        Save
      </Button>
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}
