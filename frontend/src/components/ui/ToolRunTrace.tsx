"use client";

import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { IconChevronDown, IconChevronUp } from "@tabler/icons-react";
import * as React from "react";
import { SkeletonList } from "@/components/ui/loading";
import StatusPill from "@/components/ui/StatusPill";
import type { StatusKey } from "@/theme/tokens/status";

export type ToolRunStep = {
  id: string;
  tool: string;
  status: StatusKey;
  durationMs?: number;
  output?: string;
};

type ToolRunTraceProps = {
  steps: ToolRunStep[];
  loading?: boolean;
};

export default function ToolRunTrace({ steps, loading = false }: ToolRunTraceProps) {
  const [openId, setOpenId] = React.useState<string | null>(null);

  if (loading) {
    return <SkeletonList rows={3} rowHeight={56} />;
  }
  if (steps.length === 0) {
    return <Typography variant="body2" color="text.secondary">No tool steps recorded.</Typography>;
  }

  return (
    <Box sx={{ display: "grid", gap: 1 }}>
      {steps.map((step) => {
        const open = openId === step.id;
        return (
          <Box key={step.id} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.25 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Typography variant="body2" sx={{ flexGrow: 1, fontFamily: "monospace" }}>{step.tool}</Typography>
              <StatusPill status={step.status} />
              {step.durationMs !== undefined ? (
                <Typography variant="caption" color="text.secondary">{step.durationMs}ms</Typography>
              ) : null}
              {step.output ? (
                <IconButton size="small" onClick={() => setOpenId(open ? null : step.id)} aria-label="Toggle output">
                  {open ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
                </IconButton>
              ) : null}
            </Box>
            <Collapse in={open}>
              <Typography
                component="pre"
                variant="caption"
                sx={{ mt: 1, p: 1, bgcolor: "action.hover", borderRadius: 1, overflow: "auto" }}
              >
                {step.output}
              </Typography>
            </Collapse>
          </Box>
        );
      })}
    </Box>
  );
}
