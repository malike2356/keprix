"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

type PlaybookRun = {
  object_id?: string;
  trace_id?: string;
  payload?: {
    playbook_name?: string;
    status?: string;
    dry_run?: boolean;
    steps?: Array<{
      step_id: string;
      title: string;
      status: string;
      needs_human_review?: boolean;
    }>;
    pending_approvals?: string[];
    finished_at?: string;
  };
};

type Props = {
  objects: Array<Record<string, unknown>>;
};

function asPlaybookRun(item: Record<string, unknown>): PlaybookRun | null {
  if (item.object_type !== "playbook_run") return null;
  return item as PlaybookRun;
}

export default function ResearchTimeline({ objects }: Props) {
  const runs = objects.map(asPlaybookRun).filter(Boolean) as PlaybookRun[];

  if (!runs.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No playbook runs yet.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      {runs.map((run) => {
        const payload = run.payload || {};
        return (
          <Box
            key={String(run.object_id)}
            sx={{ borderLeft: 2, borderColor: "divider", pl: 1.5, py: 0.5 }}
          >
            <Typography variant="subtitle2">
              {payload.playbook_name || "Playbook run"}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              {run.object_id} | trace {run.trace_id} | {payload.finished_at || "in progress"}
            </Typography>
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.5 }}>
              <Chip size="small" label={payload.status || "unknown"} />
              {payload.dry_run ? <Chip size="small" label="dry run" variant="outlined" /> : null}
              {(payload.pending_approvals || []).map((stepId) => (
                <Chip key={stepId} size="small" color="warning" label={`review: ${stepId}`} />
              ))}
            </Box>
            <Box component="ul" sx={{ m: 0, pl: 2, mt: 0.5 }}>
              {(payload.steps || []).map((step) => (
                <Typography component="li" variant="caption" key={step.step_id}>
                  {step.title} ({step.status})
                  {step.needs_human_review ? " [needs review]" : ""}
                </Typography>
              ))}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
