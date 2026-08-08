"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import StructuredDataView from "@/components/ui/StructuredDataView";
import type { TraceEvent, TraceView } from "@/lib/agents-runtime-api";

const eventColor: Record<string, "default" | "primary" | "secondary" | "warning" | "error" | "success" | "info"> = {
  agent_start: "primary",
  agent_end: "default",
  handoff: "secondary",
  guardrail: "warning",
  tool: "info",
  output: "success",
  realtime: "default",
};

type Props = {
  trace: TraceView | null;
};

export default function AgentTraceViewer({ trace }: Props) {
  if (!trace) {
    return (
      <Typography variant="body2" color="text.secondary">
        Start an agent run to view trace events.
      </Typography>
    );
  }

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Run {trace.run_id.slice(0, 8)} · agent {trace.current_agent}
      </Typography>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Chip size="small" label={`handoffs ${trace.summary.handoffs}`} />
        <Chip size="small" label={`guardrails ${trace.summary.guardrails}`} />
        <Chip size="small" label={`tools ${trace.summary.tools}`} />
        <Chip size="small" label={`outputs ${trace.summary.outputs}`} />
      </Box>
      <List dense>
        {trace.events.map((event: TraceEvent, index: number) => (
          <ListItem key={`${event.at}-${index}`} alignItems="flex-start" sx={{ px: 0 }}>
            <ListItemText
              primary={
                <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Chip size="small" color={eventColor[event.type] ?? "default"} label={event.type} />
                  <Typography variant="body2">{event.agent}</Typography>
                </Box>
              }
              secondary={<StructuredDataView value={event.payload} emptyLabel="-" />}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
