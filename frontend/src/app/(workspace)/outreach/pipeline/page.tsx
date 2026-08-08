"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import { PIPELINE_STAGES, pipelineLabel, type OutreachLead } from "@/components/outreach/types";
import {
  fetchOutreachPipeline,
  fetchOutreachPipelineBoard,
  patchOutreachLead,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

export default function OutreachPipelinePage() {
  const [error, setError] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);

  const board = useSWR(["outreach-pipeline-board", WORKSPACE], () => fetchOutreachPipelineBoard(WORKSPACE));
  const pipeline = useSWR(["outreach-pipeline", WORKSPACE], () => fetchOutreachPipeline(WORKSPACE));

  const columns = board.data?.columns ?? {};
  const summary = board.data?.summary ?? pipeline.data?.stages ?? {};

  const move = async (leadId: string, status: string) => {
    setBusyId(leadId);
    setError(null);
    try {
      await patchOutreachLead(leadId, { status }, WORKSPACE);
      await Promise.all([board.mutate(), pipeline.mutate()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update lead status");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Stack spacing={2}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
        <Button size="small" variant="outlined" component={Link} href="/outreach/replies">
          Reply queue
        </Button>
        <Button size="small" variant="outlined" component={Link} href="/outreach/bookings">
          Bookings
        </Button>
        {(["total", "contacted", "replied", "booked", "won", "lost", "follow_up"] as const).map((key) => (
          <Chip
            key={key}
            size="small"
            variant="outlined"
            label={`${key.replace(/_/g, " ")}: ${summary[key] ?? pipeline.data?.total ?? (key === "total" ? pipeline.data?.total ?? 0 : 0)}`}
          />
        ))}
      </Stack>

      {board.isLoading && !board.data ? (
        <Typography color="text.secondary">Loading pipeline...</Typography>
      ) : (
        <Box
          sx={{
            display: "flex",
            gap: 1.5,
            overflowX: "auto",
            pb: 1,
            minHeight: 420,
          }}
        >
          {PIPELINE_STAGES.map((status) => {
            const leads = (columns[status] ?? []) as OutreachLead[];
            return (
              <Card
                key={status}
                variant="outlined"
                sx={{ minWidth: 220, maxWidth: 260, flex: "0 0 auto", display: "flex", flexDirection: "column" }}
              >
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 }, flex: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    {pipelineLabel(status)} ({leads.length})
                  </Typography>
                  <Stack spacing={1}>
                    {leads.length === 0 ? (
                      <Typography variant="caption" color="text.secondary" sx={{ py: 2, textAlign: "center" }}>
                        Empty
                      </Typography>
                    ) : (
                      leads.map((lead) => (
                        <Box
                          key={lead.id}
                          sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1 }}
                        >
                          <Typography
                            component={Link}
                            href={`/outreach/leads/${lead.id}`}
                            variant="body2"
                            fontWeight={600}
                            sx={{ color: "primary.main", textDecoration: "none" }}
                          >
                            {lead.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" display="block" noWrap>
                            {lead.company || lead.email || lead.source || "No detail"}
                          </Typography>
                          <FormControl size="small" fullWidth sx={{ mt: 1 }}>
                            <InputLabel id={`move-${lead.id}`}>Move</InputLabel>
                            <Select
                              labelId={`move-${lead.id}`}
                              label="Move"
                              value={lead.status || status}
                              disabled={busyId === lead.id}
                              onChange={(e) => void move(lead.id, e.target.value)}
                            >
                              {PIPELINE_STAGES.map((stage) => (
                                <MenuItem key={stage} value={stage}>
                                  {pipelineLabel(stage)}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                          <Stack direction="row" spacing={0.5} sx={{ mt: 0.75 }} flexWrap="wrap" useFlexGap>
                            <Button size="small" disabled={busyId === lead.id} onClick={() => void move(lead.id, "replied")}>
                              Replied
                            </Button>
                            <Button size="small" disabled={busyId === lead.id} onClick={() => void move(lead.id, "won")}>
                              Won
                            </Button>
                            <Button size="small" disabled={busyId === lead.id} onClick={() => void move(lead.id, "lost")}>
                              Lost
                            </Button>
                          </Stack>
                        </Box>
                      ))
                    )}
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}
    </Stack>
  );
}
